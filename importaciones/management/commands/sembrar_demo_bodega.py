"""Siembra el piloto de la Bodega de Distribución para demostrar el MVP.

Los datos que siembra son **de demostración**: las constancias reales de la
carpeta de respaldo son PDF por trabajador, y el MVP todavía no modela
trabajadores (es el paso 5 de la secuencia de construcción). Lo que se siembra
son los cursos que esa carpeta acredita, elevados al grano que el MVP sí
maneja: obligaciones del centro de costo.

Cada archivo que se guarda es un marcador que lo dice en su primera línea, y
cada evidencia queda con un emisor que la identifica como dato de
demostración. Nada de esto debe confundirse con evidencia real ante
fiscalización.

Como el modelo es append-only, lo que este comando escribe **no se puede
borrar**: por eso exige `--confirmar` y se niega a sembrar dos veces.
"""

from argparse import ArgumentParser
from datetime import date
from typing import Any, cast

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from evidencias.services import cargar_evidencia, validar_evidencia
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad

from importaciones.catalogo_demo import (
    CATALOGO,
    CursoRespaldado,
    ObligacionDemo,
    SituacionDemo,
    leer_respaldo,
)


CANAL = "Siembra de demostración"
EMISOR = "Demostración — no es evidencia real"

CON_EVIDENCIA = {
    SituacionDemo.VIGENTE,
    SituacionDemo.POR_VENCER,
    SituacionDemo.VENCIDO,
    SituacionDemo.PENDIENTE_VALIDACION,
}


def marcador_pdf(lineas: list[str]) -> bytes:
    """Arma un PDF de una página que se abre y dice qué es.

    Se genera aquí, sin dependencias nuevas, porque los PDF originales de la
    carpeta de respaldo no están descargados y no hay bytes reales que guardar.
    """
    instrucciones = ["BT", "/F1 11 Tf", "40 780 Td", "16 TL"]
    for linea in lineas:
        escapada = linea.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        instrucciones.append(f"({escapada}) Tj T*")
    instrucciones.append("ET")
    flujo = "\n".join(instrucciones).encode("cp1252", "replace")

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]"
        b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(flujo)).encode("ascii")
        + b" >>\nstream\n"
        + flujo
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding >>",
    ]

    salida = bytearray(b"%PDF-1.4\n")
    posiciones: list[int] = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{numero} 0 obj\n".encode("ascii") + cuerpo + b"\nendobj\n"

    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode("ascii")
    salida += b"0000000000 65535 f \n"
    for posicion in posiciones:
        salida += f"{posicion:010d} 00000 n \n".encode("ascii")
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(salida)


def nombre_archivo(curso: str) -> str:
    """Convierte el nombre del curso en un nombre de archivo manejable."""
    limpio = "".join(c if c.isalnum() or c in " -" else "" for c in curso)
    return "demo-" + "-".join(limpio.lower().split())[:80] + ".pdf"


class Command(BaseCommand):
    help = (
        "Siembra el centro de costo de la Bodega de Distribución con las "
        "obligaciones que acredita la carpeta de respaldo, y con evidencia de "
        "demostración que hace derivar los seis estados de cumplimiento."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--usuario",
            required=True,
            help="Usuario que quedará como autor; debe pertenecer a Prevencionista.",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma la siembra; sin esta opción el comando no escribe nada.",
        )

    def handle(self, *args: Any, **opciones: Any) -> None:
        del args
        actor = self._actor(opciones["usuario"])
        respaldo = leer_respaldo()

        if CentroCosto.objects.filter(
            codigo_contable=respaldo.codigo_contable
        ).exists():
            raise CommandError(
                f"El centro de costo {respaldo.codigo_contable} ya existe. La "
                "siembra no se puede repetir: el modelo es append-only y lo "
                "escrito no se puede borrar."
            )

        faltantes = [
            curso.nombre for curso in respaldo.cursos if curso.nombre not in CATALOGO
        ]
        if faltantes:
            raise CommandError(
                "El catálogo de demostración no describe estos cursos: "
                + "; ".join(faltantes)
            )

        if not opciones["confirmar"]:
            self._anunciar(respaldo)
            self.stdout.write(
                self.style.WARNING(
                    "\nNo se escribió nada. Repite con --confirmar para sembrar."
                )
            )
            return

        with transaction.atomic():
            centro = self._crear_centro(respaldo, actor)
            for curso in respaldo.cursos:
                self._sembrar_curso(centro, curso, CATALOGO[curso.nombre], actor)

        self._resumir(respaldo, centro)

    def _actor(self, usuario: str) -> User:
        try:
            actor = User.objects.get(username=usuario)
        except User.DoesNotExist as exc:
            raise CommandError(f"No existe el usuario {usuario}.") from exc
        if not actor.groups.filter(name="Prevencionista").exists():
            raise CommandError(
                f"{usuario} no pertenece al grupo Prevencionista, y la siembra "
                "necesita validar evidencia."
            )
        return actor

    def _anunciar(self, respaldo: Any) -> None:
        self.stdout.write(
            f"Centro de costo: {respaldo.codigo_contable} — {respaldo.nombre}"
        )
        self.stdout.write(
            f"Respaldo: {respaldo.constancias_totales} constancias de "
            f"{respaldo.trabajadores_distintos} trabajadores en "
            f"{len(respaldo.cursos)} cursos."
        )
        for curso in respaldo.cursos:
            situacion = CATALOGO[curso.nombre].situacion
            self.stdout.write(f"  {curso.nombre}: {situacion.value}")

    def _crear_centro(self, respaldo: Any, actor: User) -> CentroCosto:
        centro = CentroCosto.objects.create(
            codigo_contable=respaldo.codigo_contable,
            nombre=respaldo.nombre,
            tipo=respaldo.tipo,
        )
        registrar_evento(
            actor=actor,
            accion="alta",
            entidad="centro de costo",
            identificador=str(centro.pk),
            descripcion=f"Creó el centro de costo {centro.nombre}.",
            canal=CANAL,
            contexto=ContextoBitacora.para_centro(centro),
        )
        return centro

    def _sembrar_curso(
        self,
        centro: CentroCosto,
        curso: CursoRespaldado,
        demo: ObligacionDemo,
        actor: User,
    ) -> None:
        obligacion = self._crear_obligacion(curso, demo, actor)
        aplica = demo.situacion != SituacionDemo.NO_APLICA
        motivo = (
            demo.motivo_no_aplica
            if not aplica
            else (
                f"Aplica según la carpeta de respaldo: {curso.constancias} "
                f"constancias en {curso.resumen_grupos}."
            )
        )
        CambioAplicabilidad.objects.create(
            centro_costo=centro,
            obligacion=obligacion,
            aplica=aplica,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="aplicar" if aplica else "declarar_no_aplica",
            entidad="plan de aplicación",
            identificador=str(centro.pk),
            descripcion=f"Actualizó la aplicabilidad de {obligacion}.",
            canal=CANAL,
            contexto=ContextoBitacora.para_plan(centro, obligacion),
        )

        if demo.situacion not in CON_EVIDENCIA:
            return
        self._cargar(centro, obligacion, curso, demo, actor)

    def _crear_obligacion(
        self,
        curso: CursoRespaldado,
        demo: ObligacionDemo,
        actor: User,
    ) -> Obligacion:
        obligacion = Obligacion.objects.create()
        version = VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=curso.nombre,
            norma_origen=demo.norma_origen,
            titular=TitularObligacion.CENTRO_COSTO,
            periodicidad=demo.periodicidad,
            tipos_centro=[CentroCosto.Tipo.BODEGA],
            tipo_version=TipoVersion.ALTA,
            autor=actor,
            motivo=(
                "Alta de demostración derivada de la carpeta de respaldo de la "
                "bodega. La norma de origen es preliminar y Prevención debe "
                "confirmarla."
            ),
        )
        registrar_evento(
            actor=actor,
            accion="alta",
            entidad="obligación",
            identificador=str(obligacion.pk),
            descripcion=f"Se registró {version.nombre}.",
            canal=CANAL,
            contexto=ContextoBitacora.para_obligacion(obligacion),
        )
        return obligacion

    def _cargar(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        curso: CursoRespaldado,
        demo: ObligacionDemo,
        actor: User,
    ) -> None:
        emision = cast(date, demo.fecha_emision)
        vencimiento = cast(date, demo.fecha_vencimiento)
        contenido = marcador_pdf(
            [
                "ARCHIVO DE DEMOSTRACION - NO ES EVIDENCIA REAL",
                "",
                f"Centro de costo: {centro.codigo_contable} - {centro.nombre}",
                f"Obligacion: {curso.nombre}",
                f"Emision: {emision.isoformat()}",
                f"Vencimiento: {vencimiento.isoformat()}",
                "",
                "El respaldo real son "
                f"{curso.constancias} constancias por trabajador",
                "que todavia no se pueden cargar: el MVP no modela trabajadores.",
            ]
        )
        evidencia = cargar_evidencia(
            centro=centro,
            obligacion=obligacion,
            actor=actor,
            archivo=SimpleUploadedFile(
                nombre_archivo(curso.nombre),
                contenido,
                content_type="application/pdf",
            ),
            emisor=EMISOR,
            fecha_emision=emision,
            fecha_vencimiento=vencimiento,
            canal=CANAL,
        )
        if demo.situacion != SituacionDemo.PENDIENTE_VALIDACION:
            validar_evidencia(evidencia=evidencia, actor=actor, canal=CANAL)

    def _resumir(self, respaldo: Any, centro: CentroCosto) -> None:
        self.stdout.write(
            self.style.SUCCESS(
                f"Sembrado {centro.codigo_contable} — {centro.nombre} con "
                f"{len(respaldo.cursos)} obligaciones."
            )
        )
        self.stdout.write(
            "Los archivos guardados son marcadores de demostración: los PDF "
            "originales no están descargados desde OneDrive."
        )
