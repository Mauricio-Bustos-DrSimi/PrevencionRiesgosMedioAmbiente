"""Retracta las obligaciones que el piloto atribuyó al titular equivocado.

Una bodega no tiene licencia de conducir. La tienen las personas que conducen,
cada una con su fecha. La siembra inicial del piloto atribuyó **todas** las
obligaciones al centro de costo, y catorce de las dieciocho de ADM04 tienen su
respaldo en un diploma o un examen a nombre de un trabajador: las 245
constancias de la carpeta pertenecen las 245 a una persona identificada por su
RUT, ninguna al centro.

Se retracta en vez de borrar. El modelo es append-only (ADR 0001): cada
obligación mal atribuida se cierra con una versión nueva que declara el motivo,
la evidencia cargada bajo ella queda consultable y verificable por hash, y la
retractación misma queda en la historia. Es además el ensayo de cómo se corrige
un error de datos maestros cuando esto esté en producción.

Cerrar basta: el plan del centro se arma con el catálogo vigente, y las
consultas de cumplimiento saltan las obligaciones cerradas. No hace falta,
además, un cambio de aplicabilidad, y agregarlo diría algo que no es cierto
—que el centro decidió que no le aplica— cuando lo que ocurrió es que la
obligación nunca fue suya.
"""

from argparse import ArgumentParser
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from importaciones.catalogo_demo import CATALOGO
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad


CANAL = "Retractación del piloto"

CODIGO_POR_OMISION = "ADM04"

MOTIVO_RETRACTACION = (
    "Retractación por error de atribución, no por cambio normativo: esta "
    "obligación recae sobre el trabajador y no sobre el centro de costo. Su "
    "respaldo son diplomas y exámenes a nombre de personas identificadas por "
    "su RUT. La obligación vuelve al plan cuando exista con su titular "
    "correcto; la evidencia cargada bajo ella queda consultable."
)


class Command(BaseCommand):
    help = (
        "Cierra las obligaciones del piloto cuyo respaldo es por persona y "
        "que quedaron atribuidas al centro de costo."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--usuario",
            required=True,
            help="Usuario que quedará como autor; debe pertenecer a Prevencionista.",
        )
        parser.add_argument(
            "--centro",
            default=CODIGO_POR_OMISION,
            help="Código contable del centro de costo a corregir.",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma la retractación; sin esta opción no se escribe nada.",
        )

    def handle(self, *args: Any, **opciones: Any) -> None:
        del args
        actor = self._actor(opciones["usuario"])
        centro = self._centro(opciones["centro"])
        por_retractar, ya_cerradas = self._clasificar(centro)

        self._anunciar(centro, por_retractar, ya_cerradas)

        if not por_retractar:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nNo queda nada por retractar: la corrección ya está hecha."
                )
            )
            return

        if not opciones["confirmar"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nNo se escribió nada. Repite con --confirmar para retractar."
                )
            )
            return

        with transaction.atomic():
            for obligacion in por_retractar:
                self._retractar(centro, obligacion, actor)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nRetractadas {len(por_retractar)} obligaciones de "
                f"{centro.codigo_contable}. Nada se borró: la evidencia sigue "
                "consultable y verificable por hash."
            )
        )

    # --- entradas ---------------------------------------------------------

    def _actor(self, usuario: str) -> User:
        try:
            actor = User.objects.get(username=usuario)
        except User.DoesNotExist as exc:
            raise CommandError(f"No existe el usuario {usuario}.") from exc
        if not actor.groups.filter(name="Prevencionista").exists():
            raise CommandError(
                f"{usuario} no pertenece al grupo Prevencionista, y la "
                "retractación es un acto de Prevención."
            )
        return actor

    def _centro(self, codigo: str) -> CentroCosto:
        try:
            return CentroCosto.objects.get(codigo_contable=codigo)
        except CentroCosto.DoesNotExist as exc:
            raise CommandError(f"No existe el centro de costo {codigo}.") from exc

    def _clasificar(
        self,
        centro: CentroCosto,
    ) -> tuple[list[Obligacion], list[Obligacion]]:
        """Separa lo que hay que cerrar de lo que ya se cerró antes.

        Ejecutar dos veces no puede producir cierres duplicados: la segunda vez
        todo cae en la lista de lo ya cerrado.
        """
        del_plan = (
            CambioAplicabilidad.objects.filter(centro_costo=centro)
            .select_related("obligacion")
            .prefetch_related("obligacion__versiones")
        )
        por_retractar: list[Obligacion] = []
        ya_cerradas: list[Obligacion] = []
        vistas: set[int] = set()
        for cambio in del_plan:
            obligacion = cambio.obligacion
            if obligacion.pk in vistas:
                continue
            vistas.add(obligacion.pk)
            version = obligacion.version_actual
            if version.nombre not in CATALOGO:
                continue
            if version.titular != TitularObligacion.CENTRO_COSTO:
                continue
            if obligacion.esta_vigente:
                por_retractar.append(obligacion)
            else:
                ya_cerradas.append(obligacion)
        return self._por_nombre(por_retractar), self._por_nombre(ya_cerradas)

    def _por_nombre(self, obligaciones: list[Obligacion]) -> list[Obligacion]:
        return sorted(
            obligaciones,
            key=lambda obligacion: obligacion.version_actual.nombre,
        )

    # --- retractación -----------------------------------------------------

    def _retractar(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        actor: User,
    ) -> None:
        actual = obligacion.version_actual
        version = VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=actual.numero + 1,
            nombre=actual.nombre,
            norma_origen=actual.norma_origen,
            titular=actual.titular,
            periodicidad=actual.periodicidad,
            tipos_centro=actual.tipos_centro,
            cargos_sugeridos=actual.cargos_sugeridos,
            tipo_version=TipoVersion.CIERRE,
            fecha_cierre=timezone.localdate(),
            autor=actor,
            motivo=MOTIVO_RETRACTACION,
        )
        registrar_evento(
            actor=actor,
            accion="retractar_obligacion",
            entidad="obligación",
            identificador=str(obligacion.pk),
            descripcion=(
                f"Retractó {version.nombre} en {centro.codigo_contable}: se "
                "había atribuido al centro de costo una obligación cuyo "
                "titular es el trabajador."
            ),
            canal=CANAL,
            contexto=ContextoBitacora(centro_costo=centro, obligacion=obligacion),
        )

    # --- salida -----------------------------------------------------------

    def _anunciar(
        self,
        centro: CentroCosto,
        por_retractar: list[Obligacion],
        ya_cerradas: list[Obligacion],
    ) -> None:
        self.stdout.write(
            f"Centro de costo: {centro.codigo_contable} — {centro.nombre}"
        )
        self.stdout.write(
            f"\nPor retractar ({len(por_retractar)}), porque su respaldo es "
            "por persona:"
        )
        for obligacion in por_retractar:
            self.stdout.write(f"  {obligacion.version_actual.nombre}")
        if ya_cerradas:
            self.stdout.write(f"\nYa retractadas antes ({len(ya_cerradas)}):")
            for obligacion in ya_cerradas:
                self.stdout.write(f"  {obligacion.version_actual.nombre}")
