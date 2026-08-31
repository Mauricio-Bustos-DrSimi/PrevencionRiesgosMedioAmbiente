"""Catálogo de la Bodega de Distribución para la demostración del piloto.

El archivo JSON que acompaña a este módulo se derivó de la carpeta de respaldo
del departamento (`docs/1. Adm 04  - Bodega de Distribucion`): aporta los
cursos y cuántas constancias hay por grupo de cargo. Guarda recuentos y no
nombres ni RUT, para que el catálogo pueda versionarse sin incorporar datos
personales al repositorio.

Lo que el JSON no puede aportar —la norma de origen, la periodicidad y la
situación de cumplimiento que se quiere exhibir— vive aquí, porque es una
decisión del dominio y no un dato de la carpeta.

Las normas de origen son preliminares: **Prevención debe confirmarlas** antes
de usar este catálogo para algo que no sea una demostración.
"""

import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from obligaciones.models import Periodicidad


RUTA_CATALOGO = Path(__file__).resolve().parent / "datos" / "catalogo_bodega_distribucion.json"


class SituacionDemo(StrEnum):
    """Estado de cumplimiento que cada obligación debe exhibir en la demo."""

    VIGENTE = "vigente"
    POR_VENCER = "por_vencer"
    VENCIDO = "vencido"
    PENDIENTE_VALIDACION = "pendiente_validacion"
    SIN_EVIDENCIA = "sin_evidencia"
    NO_APLICA = "no_aplica"


@dataclass(frozen=True)
class ObligacionDemo:
    norma_origen: str
    periodicidad: Periodicidad
    situacion: SituacionDemo
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    motivo_no_aplica: str = ""


# Las fechas están elegidas para que los estados se deriven solos alrededor del
# 31 de agosto de 2026, con DIAS_POR_VENCER=30, y con margen suficiente para que
# la demostración no dependa del día exacto en que se ejecute.
CATALOGO: dict[str, ObligacionDemo] = {
    "Uso y manejo de extintores": ObligacionDemo(
        norma_origen="DS 594, Título IV, párrafo 3 (prevención y combate de incendios)",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.VIGENTE,
        fecha_emision=date(2026, 6, 15),
        fecha_vencimiento=date(2027, 6, 15),
    ),
    "Examen ocupacional de altura física": ObligacionDemo(
        norma_origen="Protocolo de vigilancia para trabajo en altura física (Ley 16.744)",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.VIGENTE,
        fecha_emision=date(2026, 5, 10),
        fecha_vencimiento=date(2027, 5, 10),
    ),
    "Liderazgo en seguridad y salud para supervisores": ObligacionDemo(
        norma_origen="DS 44/2023, gestión preventiva",
        periodicidad=Periodicidad.POR_EVENTO,
        situacion=SituacionDemo.VIGENTE,
        fecha_emision=date(2026, 4, 20),
        fecha_vencimiento=date(2028, 4, 20),
    ),
    "Fortalecimiento de competencias psicosociales": ObligacionDemo(
        norma_origen="Protocolo de vigilancia de riesgos psicosociales (Ley 16.744)",
        periodicidad=Periodicidad.BIENAL,
        situacion=SituacionDemo.POR_VENCER,
        fecha_emision=date(2024, 9, 25),
        fecha_vencimiento=date(2026, 9, 25),
    ),
    "Examen ocupacional de conductor clase D": ObligacionDemo(
        norma_origen="Ley 18.290 y DS 594",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.POR_VENCER,
        fecha_emision=date(2025, 9, 15),
        fecha_vencimiento=date(2026, 9, 15),
    ),
    "Licencia de conducir": ObligacionDemo(
        norma_origen="Ley 18.290, ley de tránsito",
        periodicidad=Periodicidad.POR_EVENTO,
        situacion=SituacionDemo.POR_VENCER,
        fecha_emision=date(2021, 9, 20),
        fecha_vencimiento=date(2026, 9, 20),
    ),
    "Factores de riesgo TMERT": ObligacionDemo(
        norma_origen="DS 594 art. 110 a) y Norma Técnica TMERT",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.VENCIDO,
        fecha_emision=date(2025, 2, 10),
        fecha_vencimiento=date(2026, 2, 10),
    ),
    "Orientación en prevención de riesgos laborales": ObligacionDemo(
        norma_origen="DS 44/2023, obligación de informar los riesgos laborales",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.VENCIDO,
        fecha_emision=date(2025, 4, 1),
        fecha_vencimiento=date(2026, 4, 1),
    ),
    "Gestión del riesgo de desastre": ObligacionDemo(
        norma_origen="DS 44/2023, plan de emergencia",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.PENDIENTE_VALIDACION,
        fecha_emision=date(2026, 8, 20),
        fecha_vencimiento=date(2027, 8, 20),
    ),
    "Examen ocupacional de operadores de maquinaria": ObligacionDemo(
        norma_origen="DS 594 y protocolos de vigilancia (Ley 16.744)",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.PENDIENTE_VALIDACION,
        fecha_emision=date(2026, 8, 25),
        fecha_vencimiento=date(2027, 8, 25),
    ),
    "Análisis del Decreto Supremo 44": ObligacionDemo(
        norma_origen="DS 44/2023",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.SIN_EVIDENCIA,
    ),
    "Factores de riesgo MMC": ObligacionDemo(
        norma_origen="Ley 20.001 y DS 63/2005, manejo manual de carga",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.SIN_EVIDENCIA,
    ),
    "Prevención del consumo de alcohol y drogas": ObligacionDemo(
        norma_origen="Política interna de la empresa",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.SIN_EVIDENCIA,
    ),
    "Examen ocupacional de conductor de vehículo liviano": ObligacionDemo(
        norma_origen="Ley 18.290 y DS 594",
        periodicidad=Periodicidad.ANUAL,
        situacion=SituacionDemo.NO_APLICA,
        motivo_no_aplica=(
            "La conducción de vehículo liviano se externalizó: ningún trabajador "
            "vigente de la bodega conduce vehículos de la empresa."
        ),
    ),
}


@dataclass(frozen=True)
class CursoRespaldado:
    """Un curso tal como aparece en la carpeta de respaldo."""

    nombre: str
    constancias: int
    grupos: dict[str, int]

    @property
    def resumen_grupos(self) -> str:
        return ", ".join(
            f"{grupo} ({cantidad})" for grupo, cantidad in sorted(self.grupos.items())
        )


@dataclass(frozen=True)
class RespaldoBodega:
    codigo_contable: str
    nombre: str
    tipo: str
    trabajadores_distintos: int
    constancias_totales: int
    cursos: list[CursoRespaldado]


def leer_respaldo(ruta: Path | None = None) -> RespaldoBodega:
    """Lee el catálogo derivado de la carpeta de respaldo."""
    datos = json.loads((ruta or RUTA_CATALOGO).read_text(encoding="utf-8"))
    centro = datos["centro_costo"]
    return RespaldoBodega(
        codigo_contable=centro["codigo_contable"],
        nombre=centro["nombre"],
        tipo=centro["tipo"],
        trabajadores_distintos=datos["trabajadores_distintos"],
        constancias_totales=datos["constancias_totales"],
        cursos=[
            CursoRespaldado(
                nombre=curso["nombre"],
                constancias=curso["constancias"],
                grupos=curso["grupos"],
            )
            for curso in datos["cursos"]
        ],
    )
