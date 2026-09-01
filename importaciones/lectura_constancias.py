"""Lee la carpeta de respaldo del departamento y la traduce a datos del dominio.

La carpeta está organizada como
`<grupo de cargo>/<capacitación>[/<subtipo>]/<RUT - Nombre>/<archivo.pdf>`, y
cada PDF es la constancia de un trabajador. Las constancias de la plataforma de
e-learning traen capa de texto con la fecha en que se realizó el curso y la
fecha en que expira; los exámenes ocupacionales y las licencias de conducir son
escaneos y no traen ninguna.

Lo que este módulo produce es un resumen **sin nombres ni RUT**: recuentos por
curso y por grupo de cargo, más los pares de fechas de las constancias que las
declaran. Así el resumen puede versionarse en el repositorio sin incorporar
datos personales, y la carpeta —que sí los tiene— se queda fuera.
"""

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from trabajadores.rut import RutInvalido, normalizar_rut

from .pdf import texto_de_pdf


# Las carpetas numeran los cursos dentro de cada grupo de cargo, así que el
# mismo curso lleva números distintos según el grupo, y su nombre está escrito
# de varias maneras. Esta tabla los reduce al nombre con que la obligación vive
# en el sistema.
NOMBRE_CANONICO: dict[str, str] = {
    "fortaleciendo competencias psicosociales jefaturas": (
        "Fortalecimiento de competencias psicosociales"
    ),
    "fortaleciendo competencias psicosociales": (
        "Fortalecimiento de competencias psicosociales"
    ),
    "fortaleciendo competencias psico": (
        "Fortalecimiento de competencias psicosociales"
    ),
    "fortaleciendo comp psico": "Fortalecimiento de competencias psicosociales",
    # Las dos carpetas son el mismo curso: las 101 constancias, de una y de
    # otra, llevan impreso el mismo título. Manda lo que dice el certificado.
    "uso y manejo de extintores": "Manejo de extintores con simulador",
    "manejo de extintores con simulador": "Manejo de extintores con simulador",
    "orientacion en prevencion de riesgos laborales": (
        "Orientación en prevención de riesgos laborales"
    ),
    "prevencion del consumo de alcohol y drogas": (
        "Prevención del consumo de alcohol y drogas"
    ),
    "analisis de decreto 44": "Análisis del Decreto Supremo 44",
    "liderazgo en seguridad y salud para supervisores": (
        "Liderazgo en seguridad y salud para supervisores"
    ),
    "factores de riesgo (tmert)": "Factores de riesgo TMERT",
    "factores de riesgo (mmc)": "Factores de riesgo MMC",
    "gestion del riesgo de desastre": "Gestión del riesgo de desastre",
    "licencia de conducir": "Licencia de conducir",
}

# Los exámenes ocupacionales se separan por subtipo, porque cada uno responde a
# un protocolo de vigilancia distinto y vence por su cuenta.
SUBTIPO_CANONICO: dict[str, str] = {
    "altura fisica": "Examen ocupacional de altura física",
    "conductor clase d": "Examen ocupacional de conductor clase D",
    "operadores (tipo d)": "Examen ocupacional de operadores de maquinaria",
    "conductor de vehiculo liviano": (
        "Examen ocupacional de conductor de vehículo liviano"
    ),
}

_ES_EXAMEN = re.compile(r"^examenes?\s+ocupacionales?$")
_PREFIJO = re.compile(r"^\s*\d+\s*[.\-]\s*")
# Las carpetas de persona se llaman «<RUT> - <Nombre>», pero el separador es
# irregular: falta el guion, falta el espacio, o hay un espacio antes del
# dígito verificador. Se acepta cualquiera de esas escrituras y el RUT se
# valida después con su dígito verificador.
_RUT = re.compile(r"^\s*(\d{7,8})\s*-?\s*([\dkK])(?![\d])\s*-?\s*(.*)$")

_MESES = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

_REALIZADO = re.compile(
    r"REALIZADO:\s*(\d{1,2})\s*DE\s*([A-ZÁÉÍÓÚÑ]+)\s*DE\s*(\d{4})",
    re.IGNORECASE,
)
_EXPIRA = re.compile(
    r"EXPIRACI[ÓO]N:\s*(\d{1,2})/(\d{1,2})/(\d{4})",
    re.IGNORECASE,
)


class CarpetaIlegible(Exception):
    """La carpeta de respaldo no está donde se dijo, o no se puede recorrer."""


def _sin_tildes(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    return texto.translate(reemplazos)


def _clave(nombre: str) -> str:
    """Normaliza el nombre de una carpeta para poder compararlo."""
    return _sin_tildes(_PREFIJO.sub("", nombre)).strip().lower()


def nombre_de_obligacion(curso: str, subtipo: str) -> str | None:
    """Traduce la carpeta de curso (y su subtipo) al nombre de la obligación."""
    clave_curso = _clave(curso)
    if _ES_EXAMEN.match(clave_curso):
        return SUBTIPO_CANONICO.get(_clave(subtipo))
    return NOMBRE_CANONICO.get(clave_curso)


def fechas_de_constancia(texto: str) -> tuple[date | None, date | None]:
    """Saca la fecha de realización y la de expiración de la capa de texto."""
    emision: date | None = None
    vencimiento: date | None = None

    realizado = _REALIZADO.search(texto)
    if realizado is not None:
        mes = _MESES.get(_sin_tildes(realizado.group(2)).upper())
        if mes is not None:
            try:
                emision = date(int(realizado.group(3)), mes, int(realizado.group(1)))
            except ValueError:
                emision = None

    expira = _EXPIRA.search(texto)
    if expira is not None:
        try:
            vencimiento = date(
                int(expira.group(3)),
                int(expira.group(2)),
                int(expira.group(1)),
            )
        except ValueError:
            vencimiento = None

    if emision is not None and vencimiento is not None and vencimiento < emision:
        return None, None
    return emision, vencimiento


@dataclass(frozen=True)
class Constancia:
    """Un archivo de la carpeta, ya interpretado.

    `rut` y `nombre` identifican a la persona a la que pertenece la constancia
    y no salen nunca al resumen versionado: solo la siembra los usa, para
    atribuir la evidencia a su titular real.
    """

    obligacion: str
    grupo: str
    ruta: Path
    rut: str | None
    fecha_emision: date | None
    fecha_vencimiento: date | None
    nombre: str = ""
    carpeta_persona: str = ""

    @property
    def esta_fechada(self) -> bool:
        return self.fecha_emision is not None and self.fecha_vencimiento is not None


@dataclass
class CursoRespaldado:
    """Un curso de la carpeta, agregado y sin datos personales."""

    nombre: str
    constancias: int = 0
    grupos: dict[str, int] = field(default_factory=dict)
    fechadas: list[tuple[date, date]] = field(default_factory=list)

    @property
    def resumen_grupos(self) -> str:
        return ", ".join(
            f"{grupo} ({cantidad})" for grupo, cantidad in sorted(self.grupos.items())
        )

    @property
    def sin_fecha(self) -> int:
        return self.constancias - len(self.fechadas)


@dataclass
class RespaldoBodega:
    """El respaldo completo de un centro de costo, listo para versionar."""

    codigo_contable: str
    nombre: str
    tipo: str
    trabajadores_distintos: int
    constancias_totales: int
    cursos: list[CursoRespaldado]

    def curso(self, nombre: str) -> CursoRespaldado | None:
        for curso in self.cursos:
            if curso.nombre == nombre:
                return curso
        return None


def _persona_de(carpeta: str) -> tuple[str | None, str]:
    """Lee el RUT y el nombre de la carpeta de la persona.

    El RUT es la llave y se devuelve en su forma canónica; el nombre no sirve
    como llave, porque viene truncado y con variantes —hay 184 carpetas de
    persona para 129 personas—, pero sí sirve para mostrar a quién pertenece
    la constancia.
    """
    encontrado = _RUT.match(carpeta)
    if encontrado is None:
        return None, carpeta.strip()
    nombre = encontrado.group(3).strip(" -")
    try:
        return normalizar_rut(
            f"{encontrado.group(1)}-{encontrado.group(2)}"
        ), nombre
    except RutInvalido:
        return None, nombre


def ruta_sin_limite(raiz: Path) -> Path:
    """Devuelve la ruta en forma extendida, para saltarse MAX_PATH en Windows.

    Las carpetas de persona de la carpeta de respaldo llegan a 257 caracteres,
    y con el nombre del archivo pasan el límite de 260. Sin el prefijo, Windows
    no falla: `is_file()` devuelve `False` y los archivos desaparecen en
    silencio, que es la peor forma de perderlos.
    """
    if os.name != "nt":
        return raiz
    absoluta = raiz.resolve()
    texto = str(absoluta)
    if texto.startswith("\\\\?\\"):
        return absoluta
    if texto.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + texto[2:])
    return Path("\\\\?\\" + texto)


def leer_carpeta(raiz: Path) -> list[Constancia]:
    """Recorre la carpeta de respaldo y lee cada constancia que encuentra."""
    if not raiz.is_dir():
        raise CarpetaIlegible(f"No existe la carpeta de respaldo: {raiz}")
    raiz = ruta_sin_limite(raiz)

    constancias: list[Constancia] = []
    for archivo in sorted(raiz.rglob("*")):
        if not archivo.is_file():
            continue
        partes = archivo.relative_to(raiz).parts
        if len(partes) < 3:
            continue
        grupo, curso = partes[0], partes[1]
        # grupo/curso/persona/archivo son cuatro; el subtipo solo existe cuando
        # hay una carpeta más, como en los exámenes ocupacionales.
        subtipo = partes[2] if len(partes) > 4 else ""
        persona = partes[-2]

        obligacion = nombre_de_obligacion(curso, subtipo)
        if obligacion is None:
            continue

        try:
            emision, vencimiento = fechas_de_constancia(
                texto_de_pdf(archivo.read_bytes())
            )
        except OSError as exc:
            raise CarpetaIlegible(f"No se pudo leer {archivo.name}: {exc}") from exc

        rut, nombre = _persona_de(persona)
        constancias.append(
            Constancia(
                obligacion=obligacion,
                grupo=_PREFIJO.sub("", grupo).strip(),
                ruta=archivo,
                rut=rut,
                fecha_emision=emision,
                fecha_vencimiento=vencimiento,
                nombre=nombre,
                carpeta_persona=persona,
            )
        )
    return constancias


def resumir(
    constancias: list[Constancia],
    *,
    codigo_contable: str,
    nombre: str,
    tipo: str,
) -> RespaldoBodega:
    """Agrega las constancias por curso, sin conservar nada personal."""
    cursos: dict[str, CursoRespaldado] = {}
    ruts: set[str] = set()

    for constancia in constancias:
        curso = cursos.setdefault(
            constancia.obligacion,
            CursoRespaldado(nombre=constancia.obligacion),
        )
        curso.constancias += 1
        curso.grupos[constancia.grupo] = curso.grupos.get(constancia.grupo, 0) + 1
        if constancia.fecha_emision is not None and (
            constancia.fecha_vencimiento is not None
        ):
            curso.fechadas.append(
                (constancia.fecha_emision, constancia.fecha_vencimiento)
            )
        if constancia.rut is not None:
            ruts.add(constancia.rut)

    for curso in cursos.values():
        curso.fechadas.sort()

    return RespaldoBodega(
        codigo_contable=codigo_contable,
        nombre=nombre,
        tipo=tipo,
        trabajadores_distintos=len(ruts),
        constancias_totales=len(constancias),
        cursos=[cursos[nombre_curso] for nombre_curso in sorted(cursos)],
    )


def constancias_por_obligacion(
    constancias: list[Constancia],
) -> dict[str, list[Constancia]]:
    """Agrupa las constancias por la obligación a la que corresponden."""
    agrupadas: defaultdict[str, list[Constancia]] = defaultdict(list)
    for constancia in constancias:
        agrupadas[constancia.obligacion].append(constancia)
    return dict(agrupadas)


RUTA_RESUMEN = (
    Path(__file__).resolve().parent / "datos" / "catalogo_bodega_distribucion.json"
)


def a_diccionario(respaldo: RespaldoBodega) -> dict[str, object]:
    """Convierte el resumen a la forma que se versiona en el repositorio."""
    return {
        "centro_costo": {
            "codigo_contable": respaldo.codigo_contable,
            "nombre": respaldo.nombre,
            "tipo": respaldo.tipo,
        },
        "trabajadores_distintos": respaldo.trabajadores_distintos,
        "constancias_totales": respaldo.constancias_totales,
        "cursos": [
            {
                "nombre": curso.nombre,
                "constancias": curso.constancias,
                "grupos": dict(sorted(curso.grupos.items())),
                "fechadas": [
                    [emision.isoformat(), vencimiento.isoformat()]
                    for emision, vencimiento in curso.fechadas
                ],
            }
            for curso in respaldo.cursos
        ],
    }


def desde_diccionario(datos: dict[str, object]) -> RespaldoBodega:
    """Reconstruye el resumen a partir del archivo versionado."""
    centro = datos["centro_costo"]
    assert isinstance(centro, dict)
    cursos_crudos = datos["cursos"]
    assert isinstance(cursos_crudos, list)

    cursos: list[CursoRespaldado] = []
    for crudo in cursos_crudos:
        cursos.append(
            CursoRespaldado(
                nombre=crudo["nombre"],
                constancias=crudo["constancias"],
                grupos=dict(crudo["grupos"]),
                fechadas=[
                    (date.fromisoformat(emision), date.fromisoformat(vencimiento))
                    for emision, vencimiento in crudo["fechadas"]
                ],
            )
        )
    return RespaldoBodega(
        codigo_contable=str(centro["codigo_contable"]),
        nombre=str(centro["nombre"]),
        tipo=str(centro["tipo"]),
        trabajadores_distintos=int(str(datos["trabajadores_distintos"])),
        constancias_totales=int(str(datos["constancias_totales"])),
        cursos=cursos,
    )


def leer_resumen(ruta: Path | None = None) -> RespaldoBodega:
    """Lee el resumen versionado de la carpeta de respaldo."""
    return desde_diccionario(
        json.loads((ruta or RUTA_RESUMEN).read_text(encoding="utf-8"))
    )
