"""Siembra el piloto de la Bodega de Distribución para demostrar el MVP.

Las obligaciones y las fechas salen del respaldo real del departamento: las
constancias de la plataforma de e-learning declaran cuándo se realizó el curso
y cuándo expira, y esas son las fechas que se cargan. Lo único que el sistema
agrega es la periodicidad con que la obligación se renueva, que la fija la
matriz legal y no el proveedor del curso —y por eso está sin confirmar—.

Los estados no se declaran: se derivan. Una constancia de extintores de abril
de 2024 aparece vencida si el ciclo es anual y vigente si es trienal, y esa
diferencia es justamente lo que el piloto pone sobre la mesa.

El grano es el centro de costo, no la persona: el MVP todavía no modela
trabajadores (paso 5 de la secuencia). De cada obligación se carga la
constancia que vence primero, porque el centro deja de estar cubierto cuando
caduca la primera.

Como el modelo es append-only, lo que este comando escribe **no se puede
borrar**: por eso exige `--confirmar` y se niega a sembrar dos veces.
"""

from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from evidencias.services import cargar_evidencia, fin_de_vigencia, validar_evidencia
from obligaciones.models import (
    Obligacion,
    Periodicidad,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad

from importaciones.catalogo_demo import (
    CATALOGO,
    NO_APLICAN,
    SIN_RESPALDO,
    ObligacionCatalogo,
)
from importaciones.lectura_constancias import (
    CarpetaIlegible,
    Constancia,
    CursoRespaldado,
    RespaldoBodega,
    constancias_por_obligacion,
    leer_carpeta,
    leer_resumen,
)
from importaciones.pdf import marcador_pdf


CANAL = "Siembra del piloto"

EMISOR_PLATAFORMA = "Plataforma de capacitación de la empresa"
EMISOR_SIN_FECHA = "Fecha por confirmar: el documento escaneado no la declara"

MOTIVO_VERSION = (
    "Alta del piloto de la Bodega de Distribución. La norma de origen y la "
    "periodicidad son preliminares: Prevención debe confirmarlas contra la "
    "matriz legal antes de que este catálogo rija."
)


def nombre_archivo(curso: str) -> str:
    """Nombre neutro con que se guarda el archivo.

    Los nombres originales de los exámenes traen el RUT del trabajador. Como
    la evidencia se está cargando al grano del centro de costo y no al de la
    persona, se guarda con un nombre que no identifica a nadie.
    """
    limpio = "".join(c if c.isalnum() or c in " -" else "" for c in curso)
    return "-".join(limpio.lower().split())[:80] + ".pdf"


class Command(BaseCommand):
    help = (
        "Siembra el centro de costo de la Bodega de Distribución con las "
        "obligaciones y las fechas que acredita la carpeta de respaldo del "
        "departamento."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--usuario",
            required=True,
            help="Usuario que quedará como autor; debe pertenecer a Prevencionista.",
        )
        parser.add_argument(
            "--carpeta",
            default=None,
            help=(
                "Carpeta de respaldo. Si se indica, se guardan las constancias "
                "originales; si no, se guarda un marcador con las mismas fechas."
            ),
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma la siembra; sin esta opción el comando no escribe nada.",
        )

    def handle(self, *args: Any, **opciones: Any) -> None:
        del args
        actor = self._actor(opciones["usuario"])
        respaldo = leer_resumen()
        archivos = self._archivos(opciones["carpeta"])

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
                "El catálogo no describe la norma ni la periodicidad de: "
                + "; ".join(faltantes)
            )

        if not opciones["confirmar"]:
            self._anunciar(respaldo, archivos)
            self.stdout.write(
                self.style.WARNING(
                    "\nNo se escribió nada. Repite con --confirmar para sembrar."
                )
            )
            return

        with transaction.atomic():
            centro = self._crear_centro(respaldo, actor)
            for curso in respaldo.cursos:
                self._sembrar_respaldado(
                    centro,
                    curso,
                    CATALOGO[curso.nombre],
                    actor,
                    archivos.get(curso.nombre, []),
                )
            for nombre, catalogo in SIN_RESPALDO.items():
                self._sembrar_sin_evidencia(centro, nombre, catalogo, actor)
            for nombre, catalogo in NO_APLICAN.items():
                self._sembrar_sin_evidencia(centro, nombre, catalogo, actor)

        self._resumir(respaldo, centro, archivos)

    # --- entradas ---------------------------------------------------------

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

    def _archivos(self, carpeta: str | None) -> dict[str, list[Constancia]]:
        if carpeta is None:
            return {}
        try:
            return constancias_por_obligacion(leer_carpeta(Path(carpeta)))
        except CarpetaIlegible as exc:
            raise CommandError(str(exc)) from exc

    # --- decisiones -------------------------------------------------------

    def _constancia_que_rige(
        self,
        curso: CursoRespaldado,
        periodicidad: Periodicidad,
    ) -> tuple[date, date] | None:
        """La constancia que caduca primero: es la que descubre al centro."""
        if not curso.fechadas:
            return None
        return min(
            curso.fechadas,
            key=lambda par: fin_de_vigencia(
                fecha_emision=par[0],
                fecha_vencimiento=par[1],
                periodicidad=periodicidad,
            ),
        )

    # --- siembra ----------------------------------------------------------

    def _crear_centro(self, respaldo: RespaldoBodega, actor: User) -> CentroCosto:
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

    def _crear_obligacion(
        self,
        nombre: str,
        catalogo: ObligacionCatalogo,
        actor: User,
    ) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=nombre,
            norma_origen=catalogo.norma_origen,
            titular=TitularObligacion.CENTRO_COSTO,
            periodicidad=catalogo.periodicidad,
            tipos_centro=[CentroCosto.Tipo.BODEGA],
            tipo_version=TipoVersion.ALTA,
            autor=actor,
            motivo=MOTIVO_VERSION,
        )
        registrar_evento(
            actor=actor,
            accion="alta",
            entidad="obligación",
            identificador=str(obligacion.pk),
            descripcion=f"Se registró {nombre}.",
            canal=CANAL,
            contexto=ContextoBitacora.para_obligacion(obligacion),
        )
        return obligacion

    def _declarar_aplicabilidad(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        *,
        aplica: bool,
        motivo: str,
        actor: User,
    ) -> None:
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

    def _sembrar_respaldado(
        self,
        centro: CentroCosto,
        curso: CursoRespaldado,
        catalogo: ObligacionCatalogo,
        actor: User,
        constancias: list[Constancia],
    ) -> None:
        obligacion = self._crear_obligacion(curso.nombre, catalogo, actor)
        self._declarar_aplicabilidad(
            centro,
            obligacion,
            aplica=True,
            motivo=(
                f"Aplica según el respaldo del departamento: {curso.constancias} "
                f"constancias en {curso.resumen_grupos}."
            ),
            actor=actor,
        )

        rige = self._constancia_que_rige(curso, catalogo.periodicidad)
        if rige is None:
            # El respaldo existe pero es un escaneo sin fecha legible. Se carga
            # para que quede a la vista, y se deja sin validar: la fecha la
            # tiene que leer y confirmar Prevención.
            self._cargar_sin_fecha(centro, obligacion, curso, actor, constancias)
            return

        emision, vencimiento = rige
        self._cargar(
            centro,
            obligacion,
            curso,
            actor,
            emisor=EMISOR_PLATAFORMA,
            emision=emision,
            vencimiento=vencimiento,
            constancias=constancias,
            validar=True,
        )

    def _sembrar_sin_evidencia(
        self,
        centro: CentroCosto,
        nombre: str,
        catalogo: ObligacionCatalogo,
        actor: User,
    ) -> None:
        obligacion = self._crear_obligacion(nombre, catalogo, actor)
        motivo = catalogo.motivo or (
            "Aplica a la bodega y el respaldo del departamento no tiene nada "
            "sobre ella. Queda sin evidencia hasta que se cargue."
        )
        self._declarar_aplicabilidad(
            centro,
            obligacion,
            aplica=catalogo.aplica,
            motivo=motivo,
            actor=actor,
        )

    def _cargar_sin_fecha(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        curso: CursoRespaldado,
        actor: User,
        constancias: list[Constancia],
    ) -> None:
        hoy = timezone.localdate()
        self._cargar(
            centro,
            obligacion,
            curso,
            actor,
            emisor=EMISOR_SIN_FECHA,
            emision=hoy,
            vencimiento=hoy,
            constancias=constancias,
            validar=False,
        )

    def _cargar(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        curso: CursoRespaldado,
        actor: User,
        *,
        emisor: str,
        emision: date,
        vencimiento: date,
        constancias: list[Constancia],
        validar: bool,
    ) -> None:
        contenido = self._contenido(centro, curso, constancias, emision, vencimiento)
        evidencia = cargar_evidencia(
            centro=centro,
            obligacion=obligacion,
            actor=actor,
            archivo=SimpleUploadedFile(
                nombre_archivo(curso.nombre),
                contenido,
                content_type="application/pdf",
            ),
            emisor=emisor,
            fecha_emision=emision,
            fecha_vencimiento=vencimiento,
            canal=CANAL,
        )
        if validar:
            validar_evidencia(evidencia=evidencia, actor=actor, canal=CANAL)

    def _contenido(
        self,
        centro: CentroCosto,
        curso: CursoRespaldado,
        constancias: list[Constancia],
        emision: date,
        vencimiento: date,
    ) -> bytes:
        """El PDF original si se indicó la carpeta; si no, un marcador."""
        for constancia in constancias:
            if (constancia.fecha_emision, constancia.fecha_vencimiento) == (
                emision,
                vencimiento,
            ):
                return constancia.ruta.read_bytes()
        if constancias and not any(c.esta_fechada for c in constancias):
            return constancias[0].ruta.read_bytes()
        return marcador_pdf(
            [
                "CONSTANCIA NO ADJUNTA",
                "",
                f"Centro de costo: {centro.codigo_contable} - {centro.nombre}",
                f"Obligacion: {curso.nombre}",
                f"Emision: {emision.isoformat()}",
                f"Vencimiento: {vencimiento.isoformat()}",
                "",
                f"El respaldo son {curso.constancias} constancias por trabajador",
                "que no se adjuntaron al sembrar. Las fechas si son las reales,",
                "leidas de la constancia que caduca primero.",
            ]
        )

    # --- salida -----------------------------------------------------------

    def _anunciar(
        self,
        respaldo: RespaldoBodega,
        archivos: dict[str, list[Constancia]],
    ) -> None:
        hoy = timezone.localdate()
        self.stdout.write(
            f"Centro de costo: {respaldo.codigo_contable} — {respaldo.nombre}"
        )
        self.stdout.write(
            f"Respaldo: {respaldo.constancias_totales} constancias de "
            f"{respaldo.trabajadores_distintos} trabajadores."
        )
        self.stdout.write(
            "Archivos: "
            + (
                "las constancias originales."
                if archivos
                else "marcadores; no se indicó --carpeta."
            )
        )
        self.stdout.write(f"\nEstado que derivaría al {hoy.isoformat()}:\n")
        for curso in respaldo.cursos:
            catalogo = CATALOGO[curso.nombre]
            rige = self._constancia_que_rige(curso, catalogo.periodicidad)
            if rige is None:
                detalle = "pendiente de validación (el escaneo no trae fecha)"
            else:
                fin = fin_de_vigencia(
                    fecha_emision=rige[0],
                    fecha_vencimiento=rige[1],
                    periodicidad=catalogo.periodicidad,
                )
                detalle = (
                    f"rige la del {rige[0].isoformat()}, "
                    f"{catalogo.periodicidad.label.lower()} hasta {fin.isoformat()}"
                )
            self.stdout.write(f"  {curso.nombre}: {detalle}")
        for nombre in SIN_RESPALDO:
            self.stdout.write(f"  {nombre}: sin evidencia")
        for nombre in NO_APLICAN:
            self.stdout.write(f"  {nombre}: no aplica")

    def _resumir(
        self,
        respaldo: RespaldoBodega,
        centro: CentroCosto,
        archivos: dict[str, list[Constancia]],
    ) -> None:
        total = len(respaldo.cursos) + len(SIN_RESPALDO) + len(NO_APLICAN)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sembrado {centro.codigo_contable} — {centro.nombre} con "
                f"{total} obligaciones."
            )
        )
        if not archivos:
            self.stdout.write(
                "Los archivos guardados son marcadores: no se indicó --carpeta. "
                "Las fechas sí son las reales del respaldo."
            )
        self.stdout.write(
            "La periodicidad de cada obligación está sin confirmar, y es la que "
            "decide si una constancia aparece vigente o vencida."
        )
