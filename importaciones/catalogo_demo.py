"""Lo que la carpeta de respaldo no puede decir sobre cada obligación.

La carpeta aporta los hechos: qué cursos hay, cuánta gente los tiene, cuándo se
realizaron y cuándo expiran según la plataforma que los dictó. Lo que no aporta
es de dónde nace la obligación ni cada cuánto hay que renovarla, porque eso lo
fija la matriz legal del departamento, no el proveedor del curso.

**Las periodicidades y las normas de este módulo son preliminares.** Están
puestas para que el piloto se pueda mostrar y discutir; Prevención tiene que
confirmarlas antes de que este catálogo signifique algo. La diferencia no es
menor: las constancias otorgan tres años de vigencia, y si el ciclo real es
anual, buena parte de lo que la carpeta acredita ya está vencido. El sistema
solo deriva la consecuencia de la regla que se le dé.
"""

from dataclasses import dataclass

from obligaciones.models import Periodicidad


@dataclass(frozen=True)
class ObligacionCatalogo:
    """Una obligación del catálogo, con lo que el dominio decide sobre ella."""

    norma_origen: str
    periodicidad: Periodicidad
    aplica: bool = True
    motivo: str = ""


# Obligaciones que la carpeta de respaldo acredita. El estado de cumplimiento
# no se declara aquí: se deriva de las fechas que traen las constancias.
CATALOGO: dict[str, ObligacionCatalogo] = {
    "Manejo de extintores con simulador": ObligacionCatalogo(
        norma_origen="DS 594, Título IV, párrafo 3: prevención y combate de incendios",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Fortalecimiento de competencias psicosociales": ObligacionCatalogo(
        norma_origen="Protocolo de vigilancia de riesgos psicosociales (Ley 16.744)",
        periodicidad=Periodicidad.BIENAL,
    ),
    "Orientación en prevención de riesgos laborales": ObligacionCatalogo(
        norma_origen="DS 44/2023: obligación de informar los riesgos laborales",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Prevención del consumo de alcohol y drogas": ObligacionCatalogo(
        norma_origen="Política interna de la empresa",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Análisis del Decreto Supremo 44": ObligacionCatalogo(
        norma_origen="DS 44/2023: nuevo reglamento de gestión preventiva",
        periodicidad=Periodicidad.BIENAL,
    ),
    "Liderazgo en seguridad y salud para supervisores": ObligacionCatalogo(
        norma_origen="DS 44/2023: responsabilidades de la línea de mando",
        periodicidad=Periodicidad.BIENAL,
    ),
    "Factores de riesgo TMERT": ObligacionCatalogo(
        norma_origen="Norma Técnica TMERT y DS 594 art. 110 a)",
        periodicidad=Periodicidad.BIENAL,
    ),
    "Factores de riesgo MMC": ObligacionCatalogo(
        norma_origen="Ley 20.001 y DS 63/2005: manejo manual de carga",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Gestión del riesgo de desastre": ObligacionCatalogo(
        norma_origen="DS 44/2023: plan de emergencia y evacuación",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Examen ocupacional de altura física": ObligacionCatalogo(
        norma_origen="Protocolo de vigilancia para trabajo en altura física (Ley 16.744)",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Examen ocupacional de conductor clase D": ObligacionCatalogo(
        norma_origen="Ley 18.290 y DS 594",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Examen ocupacional de operadores de maquinaria": ObligacionCatalogo(
        norma_origen="DS 594 y protocolos de vigilancia (Ley 16.744)",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Examen ocupacional de conductor de vehículo liviano": ObligacionCatalogo(
        norma_origen="Ley 18.290 y DS 594",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Licencia de conducir": ObligacionCatalogo(
        norma_origen="Ley 18.290, ley de tránsito",
        periodicidad=Periodicidad.POR_EVENTO,
    ),
}


# Obligaciones que le corresponden a una bodega y de las que la carpeta de
# respaldo no tiene nada. Su ausencia no es un defecto de la siembra: es lo que
# el departamento verá al abrir el plan, y es el hallazgo más útil del piloto.
SIN_RESPALDO: dict[str, ObligacionCatalogo] = {
    "Matriz IPER vigente": ObligacionCatalogo(
        norma_origen="DS 44/2023: identificación de peligros y evaluación de riesgos",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Reglamento Interno de Higiene y Seguridad entregado": ObligacionCatalogo(
        norma_origen="Ley 16.744 art. 67 y DS 40, Título V",
        periodicidad=Periodicidad.ANUAL,
    ),
    "Comité Paritario de Higiene y Seguridad constituido": ObligacionCatalogo(
        norma_origen="DS 54: obligatorio sobre 25 trabajadores",
        periodicidad=Periodicidad.BIENAL,
    ),
}


# Obligaciones del catálogo general que a esta bodega no le tocan. Se siembran
# para que la demostración muestre que «No aplica» es una decisión registrada,
# con autor y motivo, y no una fila en blanco.
NO_APLICAN: dict[str, ObligacionCatalogo] = {
    "Vigilancia de exposición ocupacional a sílice": ObligacionCatalogo(
        norma_origen="PLANESI, protocolo de vigilancia de exposición a sílice",
        periodicidad=Periodicidad.ANUAL,
        aplica=False,
        motivo=(
            "En la bodega no hay proceso que genere sílice respirable: no se "
            "corta, perfora ni pule material que la contenga."
        ),
    ),
}
