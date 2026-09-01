"""Siembra el piloto de la Bodega de Distribución para demostrar el MVP.

Las obligaciones y las fechas salen del respaldo real del departamento: las
constancias de la plataforma de e-learning declaran cuándo se realizó el curso
y cuándo expira, y esas son las fechas que se cargan. Lo único que el sistema
agrega es la periodicidad con que la obligación se renueva, que la fija la
matriz legal y no el proveedor del curso —y por eso está sin confirmar—.

Los estados no se declaran: se derivan. Una constancia de extintores de abril
de 2024 aparece vencida si el ciclo es anual y vigente si es trienal, y esa
diferencia es justamente lo que el piloto pone sobre la mesa.

**El grano es el titular que declara el catálogo.** Las catorce obligaciones
que la carpeta acredita son del trabajador, así que se cargan las 245
constancias, cada una a nombre de la persona cuyo RUT nombra su carpeta, y se
da de alta a las 129 personas con el cargo que declara el nivel que las
contiene. Las que sí son de la instalación —matriz IPER, reglamento interno,
comité paritario, vigilancia de sílice— siguen colgando del centro de costo.

Atribuir exige la carpeta original: el resumen versionado es anónimo a
propósito y no basta. Sembrar sin ella **falla con ese motivo** en vez de
degradar en silencio a la carga por centro de costo.

Como el modelo es append-only, lo que este comando escribe **no se puede
borrar**: por eso exige `--confirmar` y se niega a sembrar dos veces.
"""

from argparse import ArgumentParser
from collections import defaultdict
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
from evidencias.services import cargar_evidencia, validar_evidencia
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad
from trabajadores.models import Trabajador
from trabajadores.services import crear_trabajador, validar_trabajador

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
    leer_carpeta,
    leer_resumen,
)


CANAL = "Siembra del piloto"

EMISOR_PLATAFORMA = "Plataforma de capacitación de la empresa"
EMISOR_SIN_FECHA = "Fecha por confirmar: el documento escaneado no la declara"

MOTIVO_VERSION = (
    "Alta del piloto de la Bodega de Distribución. La norma de origen y la "
    "periodicidad son preliminares: Prevención debe confirmarlas contra la "
    "matriz legal antes de que este catálogo rija."
)

MOTIVO_ALTA_TRABAJADOR = (
    "Alta desde la carpeta de respaldo del departamento: la persona aparece "
    "con constancias a su nombre en el respaldo de la Bodega de Distribución."
)

MOTIVO_PLAN_TRABAJADOR = (
    "Plan individual confirmado al sembrar, a partir de la sugerencia del "
    "cargo y de lo que la carpeta de respaldo acredita a su nombre."
)

FALTA_LA_CARPETA = (
    "Estas obligaciones son del trabajador y su respaldo son constancias a "
    "nombre de personas: {obligaciones}.\n"
    "El resumen versionado es anónimo a propósito —no lleva nombres ni RUT— y "
    "no permite atribuirlas. Vuelve a ejecutar con --carpeta apuntando a la "
    "carpeta de respaldo original. No se siembra por centro de costo: eso es "
    "justamente el error que se corrigió."
)


def nombre_archivo(curso: str, rut: str) -> str:
    """Nombre del archivo guardado: la obligación y el RUT de su titular.

    La evidencia acredita a una persona, así que su archivo la nombra. Quién
    puede abrirlo es otra pregunta —un examen ocupacional es un dato de salud—
    y se resuelve con el rol Encargado, que todavía no existe.
    """
    limpio = "".join(c if c.isalnum() or c in " -" else "" for c in curso)
    return "-".join(limpio.lower().split())[:60] + f"-{rut}.pdf"


class Command(BaseCommand):
    help = (
        "Siembra el centro de costo de la Bodega de Distribución con las "
        "obligaciones, los trabajadores y las constancias que acredita la "
        "carpeta de respaldo del departamento."
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
                "Carpeta de respaldo original. Obligatoria si el catálogo "
                "declara obligaciones de titular trabajador: sin ella no hay "
                "a quién atribuir las constancias."
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
        constancias = self._constancias(opciones["carpeta"])

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

        self._exigir_carpeta_para_atribuir(respaldo, constancias)
        sin_titular = [c for c in constancias if c.rut is None]
        if sin_titular:
            raise CommandError(self._mensaje_sin_titular(sin_titular))

        if not opciones["confirmar"]:
            self._anunciar(respaldo, constancias)
            self.stdout.write(
                self.style.WARNING(
                    "\nNo se escribió nada. Repite con --confirmar para sembrar."
                )
            )
            return

        with transaction.atomic():
            centro = self._crear_centro(respaldo, actor)
            obligaciones = {
                curso.nombre: self._crear_obligacion(
                    curso.nombre,
                    CATALOGO[curso.nombre],
                    actor,
                    cargos=sorted(curso.grupos),
                )
                for curso in respaldo.cursos
            }
            for nombre, catalogo in {**SIN_RESPALDO, **NO_APLICAN}.items():
                obligacion = self._crear_obligacion(nombre, catalogo, actor)
                self._declarar_aplicabilidad_del_centro(
                    centro,
                    obligacion,
                    catalogo,
                    actor,
                )
            trabajadores = self._dar_de_alta(centro, constancias, actor)
            self._confirmar_planes(
                trabajadores,
                obligaciones,
                constancias,
                respaldo,
                actor,
            )
            self._cargar_constancias(
                centro,
                obligaciones,
                trabajadores,
                constancias,
                actor,
            )

        self._resumir(respaldo, centro, constancias)

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

    def _constancias(self, carpeta: str | None) -> list[Constancia]:
        if carpeta is None:
            return []
        try:
            return leer_carpeta(Path(carpeta))
        except CarpetaIlegible as exc:
            raise CommandError(str(exc)) from exc

    def _exigir_carpeta_para_atribuir(
        self,
        respaldo: RespaldoBodega,
        constancias: list[Constancia],
    ) -> None:
        del_trabajador = [
            curso.nombre
            for curso in respaldo.cursos
            if CATALOGO[curso.nombre].titular == TitularObligacion.TRABAJADOR
        ]
        if del_trabajador and not constancias:
            raise CommandError(
                FALTA_LA_CARPETA.format(obligaciones="; ".join(del_trabajador))
            )

    def _mensaje_sin_titular(self, constancias: list[Constancia]) -> str:
        carpetas = sorted({c.carpeta_persona for c in constancias})
        return (
            f"{len(constancias)} constancias no dicen a quién pertenecen: su "
            "carpeta no trae un RUT válido. Corrígelo en el origen antes de "
            "sembrar; inventar una dotación no es una opción.\n  "
            + "\n  ".join(carpetas)
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
        *,
        cargos: list[str] | None = None,
    ) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=nombre,
            norma_origen=catalogo.norma_origen,
            titular=catalogo.titular,
            periodicidad=catalogo.periodicidad,
            tipos_centro=[CentroCosto.Tipo.BODEGA],
            cargos_sugeridos=cargos or [],
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

    def _declarar_aplicabilidad_del_centro(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        catalogo: ObligacionCatalogo,
        actor: User,
    ) -> None:
        motivo = catalogo.motivo or (
            "Aplica a la bodega y el respaldo del departamento no tiene nada "
            "sobre ella. Queda sin evidencia hasta que se cargue."
        )
        CambioAplicabilidad.objects.create(
            centro_costo=centro,
            obligacion=obligacion,
            aplica=catalogo.aplica,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="aplicar" if catalogo.aplica else "declarar_no_aplica",
            entidad="plan de aplicación",
            identificador=str(centro.pk),
            descripcion=f"Actualizó la aplicabilidad de {obligacion}.",
            canal=CANAL,
            contexto=ContextoBitacora.para_plan(centro, obligacion),
        )

    def _dar_de_alta(
        self,
        centro: CentroCosto,
        constancias: list[Constancia],
        actor: User,
    ) -> dict[str, Trabajador]:
        """Crea una sola persona por RUT, aunque aparezca en varios cursos."""
        trabajadores: dict[str, Trabajador] = {}
        for rut, nombre, cargo in self._personas(constancias):
            trabajador = crear_trabajador(
                rut=rut,
                nombre=nombre,
                cargo=cargo,
                centro=centro,
                motivo=MOTIVO_ALTA_TRABAJADOR,
                actor=actor,
                canal=CANAL,
            )
            validar_trabajador(trabajador=trabajador, actor=actor, canal=CANAL)
            trabajadores[rut] = trabajador
        return trabajadores

    def _personas(
        self,
        constancias: list[Constancia],
    ) -> list[tuple[str, str, str]]:
        """Reduce las constancias a una persona por RUT.

        Del nombre se queda con la escritura más larga: las carpetas lo traen
        truncado de varias formas y el RUT es la única llave confiable. Del
        cargo, con el nivel de carpeta que más constancias suyas contiene.
        """
        nombres: dict[str, str] = {}
        cargos: dict[str, defaultdict[str, int]] = {}
        for constancia in constancias:
            rut = constancia.rut
            assert rut is not None
            if len(constancia.nombre) > len(nombres.get(rut, "")):
                nombres[rut] = constancia.nombre
            cargos.setdefault(rut, defaultdict(int))[constancia.grupo] += 1
        return [
            (
                rut,
                nombres[rut] or rut,
                max(cargos[rut].items(), key=lambda par: (par[1], par[0]))[0],
            )
            for rut in sorted(nombres)
        ]

    def _confirmar_planes(
        self,
        trabajadores: dict[str, Trabajador],
        obligaciones: dict[str, Obligacion],
        constancias: list[Constancia],
        respaldo: RespaldoBodega,
        actor: User,
    ) -> None:
        """Confirma el plan individual de cada persona, uno por uno.

        Parte de la sugerencia del cargo —los cursos que ese nivel de carpeta
        tiene— y agrega lo que la carpeta acredita a nombre de la persona. Que
        una obligación quede en el plan sin constancia es el punto: así se ve
        cuántos faltan, y no solo quiénes están cubiertos.
        """
        por_cargo: defaultdict[str, set[str]] = defaultdict(set)
        for curso in respaldo.cursos:
            for grupo in curso.grupos:
                por_cargo[grupo].add(curso.nombre)
        acreditadas: defaultdict[str, set[str]] = defaultdict(set)
        for constancia in constancias:
            assert constancia.rut is not None
            acreditadas[constancia.rut].add(constancia.obligacion)

        for rut, trabajador in trabajadores.items():
            del_plan = por_cargo[trabajador.cargo] | acreditadas[rut]
            for nombre in sorted(del_plan):
                CambioAplicabilidad.objects.create(
                    trabajador=trabajador,
                    obligacion=obligaciones[nombre],
                    aplica=True,
                    motivo=MOTIVO_PLAN_TRABAJADOR,
                    autor=actor,
                )
            registrar_evento(
                actor=actor,
                accion="confirmar_sugerencia_trabajador",
                entidad="plan de aplicación",
                identificador=trabajador.rut,
                descripcion=(
                    f"Confirmó el plan individual de {trabajador.nombre} "
                    f"({trabajador.cargo}): {len(del_plan)} obligaciones."
                ),
                canal=CANAL,
                contexto=ContextoBitacora.para_trabajador(
                    trabajador,
                    trabajador.centro_costo_actual,
                ),
            )

    def _cargar_constancias(
        self,
        centro: CentroCosto,
        obligaciones: dict[str, Obligacion],
        trabajadores: dict[str, Trabajador],
        constancias: list[Constancia],
        actor: User,
    ) -> None:
        hoy = timezone.localdate()
        for constancia in constancias:
            assert constancia.rut is not None
            trabajador = trabajadores[constancia.rut]
            if constancia.esta_fechada:
                assert constancia.fecha_emision is not None
                assert constancia.fecha_vencimiento is not None
                emisor = EMISOR_PLATAFORMA
                emision: date = constancia.fecha_emision
                vencimiento: date = constancia.fecha_vencimiento
            else:
                # El escaneo no trae capa de texto. Se carga igual para que
                # esté a la vista y queda pendiente de validación: la fecha la
                # lee y la corrige Prevención, persona por persona.
                emisor = EMISOR_SIN_FECHA
                emision = hoy
                vencimiento = hoy
            evidencia = cargar_evidencia(
                centro=centro,
                obligacion=obligaciones[constancia.obligacion],
                actor=actor,
                archivo=SimpleUploadedFile(
                    nombre_archivo(constancia.obligacion, constancia.rut),
                    constancia.ruta.read_bytes(),
                    content_type="application/pdf",
                ),
                emisor=emisor,
                fecha_emision=emision,
                fecha_vencimiento=vencimiento,
                trabajador=trabajador,
                canal=CANAL,
            )
            if constancia.esta_fechada:
                validar_evidencia(evidencia=evidencia, actor=actor, canal=CANAL)

    # --- salida -----------------------------------------------------------

    def _anunciar(
        self,
        respaldo: RespaldoBodega,
        constancias: list[Constancia],
    ) -> None:
        self.stdout.write(
            f"Centro de costo: {respaldo.codigo_contable} — {respaldo.nombre}"
        )
        personas = self._personas(constancias)
        self.stdout.write(
            f"Carpeta: {len(constancias)} constancias de {len(personas)} "
            "trabajadores, cada una a nombre de su titular."
        )
        sin_fecha = len([c for c in constancias if not c.esta_fechada])
        self.stdout.write(
            f"{sin_fecha} constancias sin fecha legible quedarán pendientes de "
            "validación, una por persona."
        )
        self.stdout.write("\nObligaciones que se sembrarían:\n")
        for curso in respaldo.cursos:
            catalogo = CATALOGO[curso.nombre]
            self.stdout.write(
                f"  {curso.nombre}: titular {catalogo.titular.label.lower()}, "
                f"{self._cuantas(curso, constancias)} constancias"
            )
        for nombre in SIN_RESPALDO:
            self.stdout.write(f"  {nombre}: titular centro de costo, sin evidencia")
        for nombre in NO_APLICAN:
            self.stdout.write(f"  {nombre}: titular centro de costo, no aplica")

    def _cuantas(self, curso: CursoRespaldado, constancias: list[Constancia]) -> int:
        return len([c for c in constancias if c.obligacion == curso.nombre])

    def _resumir(
        self,
        respaldo: RespaldoBodega,
        centro: CentroCosto,
        constancias: list[Constancia],
    ) -> None:
        total = len(respaldo.cursos) + len(SIN_RESPALDO) + len(NO_APLICAN)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sembrado {centro.codigo_contable} — {centro.nombre} con "
                f"{total} obligaciones, "
                f"{len(self._personas(constancias))} trabajadores y "
                f"{len(constancias)} constancias atribuidas a su titular."
            )
        )
        self.stdout.write(
            "La periodicidad de cada obligación está sin confirmar, y es la que "
            "decide si una constancia aparece vigente o vencida."
        )
