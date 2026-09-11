from dataclasses import dataclass, replace
from typing import Protocol, Sequence
from urllib.parse import urlencode

from django.urls import reverse

from centros_costo.models import CentroCosto
from evidencias.filtros import (
    admite_centro,
    normalizar_identificador,
    normalizar_tipo_centro,
)
from evidencias.services import EstadoCumplimiento
from trabajadores.models import Trabajador


class CasoParaDashboard(Protocol):
    @property
    def centro(self) -> CentroCosto: ...

    @property
    def estado(self) -> EstadoCumplimiento: ...

    @property
    def trabajador(self) -> Trabajador | None: ...


@dataclass(frozen=True)
class FiltrosPortada:
    centro: int | None
    tipo_centro: str

    @classmethod
    def desde_parametros(cls, centro: str, tipo_centro: str) -> "FiltrosPortada":
        return cls(
            centro=normalizar_identificador(centro),
            tipo_centro=normalizar_tipo_centro(tipo_centro),
        )

    def admite_centro(self, centro: CentroCosto) -> bool:
        return admite_centro(
            centro,
            centro_id=self.centro,
            tipo_centro=self.tipo_centro,
        )

    def parametros(self) -> dict[str, str]:
        parametros: dict[str, str] = {}
        if self.centro is not None:
            parametros["centro"] = str(self.centro)
        if self.tipo_centro:
            parametros["tipo_centro"] = self.tipo_centro
        return parametros


@dataclass(frozen=True)
class KpiDashboard:
    etiqueta: str
    parametro_estado: str
    variante: str
    cantidad_centros: int
    cantidad_trabajadores: int
    url_centros: str = ""
    url_trabajadores: str = ""


@dataclass(frozen=True)
class BarraEstado:
    etiqueta: str
    variante: str
    cantidad: int
    ancho: int
    y_barra: int
    y_texto: int


@dataclass(frozen=True)
class DistribucionDashboard:
    etiqueta: str
    titular: str
    barras: tuple[BarraEstado, ...]


@dataclass(frozen=True)
class ResumenDashboard:
    kpis: tuple[KpiDashboard, ...]
    distribuciones: tuple[DistribucionDashboard, ...]
    maximo: int


ESTADOS_VISUALES = (
    (EstadoCumplimiento.VIGENTE, "Vigente", "vigente", "vigente"),
    (EstadoCumplimiento.POR_VENCER, "Por vencer", "por-vencer", "por_vencer"),
    (EstadoCumplimiento.VENCIDO, "Vencido", "vencido", "vencido"),
    (
        EstadoCumplimiento.PENDIENTE_VALIDACION,
        "Pendiente de validación",
        "pendiente",
        "pendiente_validacion",
    ),
    (
        EstadoCumplimiento.SIN_EVIDENCIA,
        "Sin evidencia",
        "sin-evidencia",
        "sin_evidencia",
    ),
    (EstadoCumplimiento.NO_APLICA, "No aplica", "no-aplica", "no_aplica"),
)

KPI_VISUALES = (
    (EstadoCumplimiento.VENCIDO, "Vencidas", "vencido", "vencido"),
    (
        EstadoCumplimiento.SIN_EVIDENCIA,
        "Sin evidencia",
        "sin-evidencia",
        "sin_evidencia",
    ),
    (
        EstadoCumplimiento.PENDIENTE_VALIDACION,
        "Pendientes de validación",
        "pendiente",
        "pendiente_validacion",
    ),
    (EstadoCumplimiento.POR_VENCER, "Por vencer", "por-vencer", "por_vencer"),
)


def resumir_casos(casos: Sequence[CasoParaDashboard]) -> ResumenDashboard:
    conteos = {
        (estado, titular): 0
        for estado, _, _, _ in ESTADOS_VISUALES
        for titular in ("centro_costo", "trabajador")
    }
    for caso in casos:
        titular = "trabajador" if caso.trabajador is not None else "centro_costo"
        conteos[(caso.estado, titular)] += 1

    maximo = max(conteos.values(), default=0)
    kpis = tuple(
        KpiDashboard(
            etiqueta=etiqueta,
            parametro_estado=parametro,
            variante=variante,
            cantidad_centros=conteos[(estado, "centro_costo")],
            cantidad_trabajadores=conteos[(estado, "trabajador")],
        )
        for estado, etiqueta, variante, parametro in KPI_VISUALES
    )
    distribuciones = tuple(
        DistribucionDashboard(
            etiqueta=etiqueta_titular,
            titular=titular,
            barras=tuple(
                BarraEstado(
                    etiqueta=etiqueta,
                    variante=variante,
                    cantidad=conteos[(estado, titular)],
                    ancho=(
                        round(conteos[(estado, titular)] * 360 / maximo)
                        if maximo
                        else 0
                    ),
                    y_barra=indice * 36 + 8,
                    y_texto=indice * 36 + 20,
                )
                for indice, (estado, etiqueta, variante, _) in enumerate(
                    ESTADOS_VISUALES
                )
            ),
        )
        for titular, etiqueta_titular in (
            ("centro_costo", "Obligaciones de instalaciones"),
            ("trabajador", "Obligaciones por trabajador"),
        )
    )
    return ResumenDashboard(kpis=kpis, distribuciones=distribuciones, maximo=maximo)


def _url_operacion(
    filtros: FiltrosPortada,
    *,
    estado: str,
    titular: str,
) -> str:
    parametros = {"estado": estado, "titular": titular} | filtros.parametros()
    return f"{reverse('evidencias:operacion')}?{urlencode(parametros)}"


def enlazar_kpis(
    resumen: ResumenDashboard,
    filtros: FiltrosPortada,
) -> ResumenDashboard:
    return replace(
        resumen,
        kpis=tuple(
            replace(
                kpi,
                url_centros=_url_operacion(
                    filtros,
                    estado=kpi.parametro_estado,
                    titular="centro_costo",
                ),
                url_trabajadores=_url_operacion(
                    filtros,
                    estado=kpi.parametro_estado,
                    titular="trabajador",
                ),
            )
            for kpi in resumen.kpis
        ),
    )


def url_accion(filtros: FiltrosPortada, *, estado: str) -> str:
    parametros = {"estado": estado} | filtros.parametros()
    return f"{reverse('evidencias:operacion')}?{urlencode(parametros)}"
