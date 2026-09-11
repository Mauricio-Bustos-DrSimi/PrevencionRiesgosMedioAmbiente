from dataclasses import dataclass

from django.http import HttpRequest

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion
from trabajadores.models import Trabajador

from .services import CasoCumplimiento, EstadoCumplimiento


ESTADOS_POR_FILTRO = {
    "vigente": EstadoCumplimiento.VIGENTE,
    "por_vencer": EstadoCumplimiento.POR_VENCER,
    "vencido": EstadoCumplimiento.VENCIDO,
    "pendiente_validacion": EstadoCumplimiento.PENDIENTE_VALIDACION,
    "sin_evidencia": EstadoCumplimiento.SIN_EVIDENCIA,
    "no_aplica": EstadoCumplimiento.NO_APLICA,
}

TITULARES_POR_FILTRO = (
    ("centro_costo", "Instalación"),
    ("trabajador", "Trabajador"),
)


def normalizar_identificador(valor: str) -> int | None:
    try:
        return int(valor)
    except ValueError:
        return None


def normalizar_tipo_centro(valor: str) -> str:
    return valor if valor in CentroCosto.Tipo.values else ""


def admite_centro(
    centro: CentroCosto,
    *,
    centro_id: int | None,
    tipo_centro: str,
) -> bool:
    return (
        (centro_id is None or centro.pk == centro_id)
        and (not tipo_centro or centro.tipo == tipo_centro)
    )


def _trabajadores_operables() -> list[Trabajador]:
    return list(
        Trabajador.objects.filter(
            asignaciones__centro_costo__es_franquicia=False,
        ).distinct()
    )


@dataclass(frozen=True)
class FiltroOperativo:
    """Filtros GET existentes y separación visual opcional por titular."""

    tipo_centro: str
    centro: int | None
    obligacion: int | None
    trabajador: int | None
    titular: str

    @classmethod
    def desde(
        cls,
        request: HttpRequest,
        *,
        incluir_titular: bool = False,
    ) -> "FiltroOperativo":
        titular = request.GET.get("titular", "") if incluir_titular else ""
        titulares_validos = {valor for valor, _ in TITULARES_POR_FILTRO}
        return cls(
            tipo_centro=normalizar_tipo_centro(
                request.GET.get("tipo_centro", "")
            ),
            centro=normalizar_identificador(request.GET.get("centro", "")),
            obligacion=normalizar_identificador(
                request.GET.get("obligacion", "")
            ),
            trabajador=normalizar_identificador(
                request.GET.get("trabajador", "")
            ),
            titular=titular if titular in titulares_validos else "",
        )

    def admite(self, caso: CasoCumplimiento) -> bool:
        trabajador = caso.trabajador
        es_trabajador = trabajador is not None
        return (
            admite_centro(
                caso.centro,
                centro_id=self.centro,
                tipo_centro=self.tipo_centro,
            )
            and (self.obligacion is None or caso.obligacion.pk == self.obligacion)
            and (
                self.trabajador is None
                or (trabajador is not None and trabajador.pk == self.trabajador)
            )
            and (
                not self.titular
                or (self.titular == "trabajador") == es_trabajador
            )
        )

    def como_contexto(self) -> dict[str, object]:
        return {
            "tipo_centro_seleccionado": self.tipo_centro,
            "tipos_centro": CentroCosto.Tipo.choices,
            "centro_seleccionado": self.centro,
            "centros": CentroCosto.objects.filter(es_franquicia=False),
            "obligacion_seleccionada": self.obligacion,
            "obligaciones": Obligacion.objects.prefetch_related("versiones").all(),
            "trabajador_seleccionado": self.trabajador,
            "trabajadores": _trabajadores_operables(),
            "titular_seleccionado": self.titular,
            "titulares": TITULARES_POR_FILTRO,
        }
