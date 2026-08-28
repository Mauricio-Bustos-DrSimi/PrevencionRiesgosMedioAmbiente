import csv
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from bitacora.registro import registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Periodicidad, TitularObligacion, TipoVersion, VersionObligacion
from obligaciones.models import Obligacion


@dataclass(frozen=True)
class ResultadoFila:
    numero: int
    estado: str
    detalle: str


@dataclass(frozen=True)
class ResultadoImportacion:
    filas: tuple[ResultadoFila, ...]

    @property
    def aceptadas(self) -> int:
        return sum(fila.estado == "Aceptada" for fila in self.filas)

    @property
    def rechazadas(self) -> int:
        return sum(fila.estado == "Rechazada" for fila in self.filas)

    @property
    def duplicadas(self) -> int:
        return sum(fila.estado == "Duplicada" for fila in self.filas)


def _filas(archivo: TextIO) -> Iterable[tuple[int, dict[str, str]]]:
    muestra = archivo.read(4096)
    archivo.seek(0)
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=",;	")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader(archivo, dialect=dialecto)
    for numero, fila in enumerate(lector, start=2):
        yield numero, {str(clave).strip(): (valor or "").strip() for clave, valor in fila.items()}


def _bool(valor: str) -> bool:
    return valor.lower() in {"1", "si", "sí", "true", "verdadero", "x"}


def importar_centros(archivo: TextIO, actor: User) -> ResultadoImportacion:
    resultados: list[ResultadoFila] = []
    vistos: set[str] = set()
    for numero, fila in _filas(archivo):
        codigo = fila.get("codigo_contable", "")
        tipo = fila.get("tipo", "")
        if not codigo or not fila.get("nombre") or tipo not in CentroCosto.Tipo.values:
            resultados.append(ResultadoFila(numero, "Rechazada", "Código, nombre o tipo inválido."))
            continue
        if codigo in vistos or CentroCosto.objects.filter(codigo_contable=codigo).exists():
            resultados.append(ResultadoFila(numero, "Duplicada", f"El código {codigo} ya existe."))
            continue
        try:
            with transaction.atomic():
                centro = CentroCosto.objects.create(
                    codigo_contable=codigo,
                    nombre=fila["nombre"],
                    tipo=tipo,
                    cve_unidad=fila.get("cve_unidad", ""),
                    es_franquicia=_bool(fila.get("es_franquicia", "")),
                )
                registrar_evento(
                    actor=actor,
                    accion="importar_alta",
                    entidad="Centro de costo",
                    identificador=codigo,
                    descripcion=f"Alta importada del centro {fila['nombre']}.",
                    canal="importación",
                    centro_costo=centro,
                )
        except IntegrityError:
            resultados.append(ResultadoFila(numero, "Duplicada", f"El código {codigo} ya existe."))
            continue
        vistos.add(codigo)
        detalle = "Franquicia excluida de la operación." if _bool(fila.get("es_franquicia", "")) else "Centro incorporado."
        resultados.append(ResultadoFila(numero, "Aceptada", detalle))
    return ResultadoImportacion(tuple(resultados))


def importar_obligaciones(archivo: TextIO, actor: User) -> ResultadoImportacion:
    resultados: list[ResultadoFila] = []
    vistos: set[str] = set()
    for numero, fila in _filas(archivo):
        nombre = fila.get("nombre", "")
        titular = fila.get("titular", "")
        periodicidad = fila.get("periodicidad", "")
        if (
            not nombre
            or not fila.get("norma_origen")
            or titular not in TitularObligacion.values
            or periodicidad not in Periodicidad.values
        ):
            resultados.append(ResultadoFila(numero, "Rechazada", "Nombre, norma, titular o periodicidad inválidos."))
            continue
        if nombre in vistos or VersionObligacion.objects.filter(
            numero=1, nombre=nombre, tipo_version=TipoVersion.ALTA
        ).exists():
            resultados.append(ResultadoFila(numero, "Duplicada", f"La obligación {nombre} ya existe."))
            continue
        tipos = [tipo for tipo in fila.get("tipos_centro", "").split("|") if tipo in CentroCosto.Tipo.values]
        if fila.get("tipos_centro") and len(tipos) != len(fila["tipos_centro"].split("|")):
            resultados.append(ResultadoFila(numero, "Rechazada", "Tipo de centro sugerido inválido."))
            continue
        try:
            with transaction.atomic():
                obligacion = Obligacion.objects.create()
                VersionObligacion.objects.create(
                    obligacion=obligacion,
                    numero=1,
                    nombre=nombre,
                    norma_origen=fila["norma_origen"],
                    titular=titular,
                    periodicidad=periodicidad,
                    tipos_centro=tipos,
                    tipo_version=TipoVersion.ALTA,
                    autor=actor,
                    motivo=fila.get("motivo") or "Alta por importación.",
                )
                registrar_evento(
                    actor=actor,
                    accion="importar_alta",
                    entidad="Obligación",
                    identificador=str(obligacion.pk),
                    descripcion=f"Alta importada de {nombre}.",
                    canal="importación",
                    obligacion=obligacion,
                )
        except IntegrityError:
            resultados.append(ResultadoFila(numero, "Duplicada", f"La obligación {nombre} ya existe."))
            continue
        vistos.add(nombre)
        resultados.append(ResultadoFila(numero, "Aceptada", "Obligación incorporada."))
    return ResultadoImportacion(tuple(resultados))
