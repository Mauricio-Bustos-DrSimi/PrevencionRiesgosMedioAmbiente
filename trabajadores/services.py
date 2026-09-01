"""Los actos sobre la dotación: alta, validación, traslado y baja.

Todos son append-only y todos quedan en la bitácora. La dotación tiene que ser
tan comprobable como la evidencia: sin saber quién estaba dónde y cuándo, el
estado agregado de un centro de costo en una fecha pasada no significa nada.
"""

from dataclasses import dataclass
from datetime import date

from django.contrib.auth.models import User
from django.db import transaction

from acceso.permisos import exigir_prevencionista
from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from configuracion.tiempo import fin_del_dia

from .models import (
    AsignacionTrabajador,
    TipoAsignacion,
    Trabajador,
    ValidacionTrabajador,
)
from .rut import RutInvalido, normalizar_rut


class ErrorDotacion(Exception):
    """El acto sobre la dotación no se puede registrar tal como se pidió."""


def crear_trabajador(
    *,
    rut: str,
    nombre: str,
    cargo: str,
    centro: CentroCosto,
    motivo: str,
    actor: User,
    canal: str = "web",
) -> Trabajador:
    """Da de alta a una persona y la asigna a su centro de costo.

    Nace no validada: quien la crea no la incorpora. Prevención la valida.
    """
    try:
        canonico = normalizar_rut(rut)
    except RutInvalido as exc:
        raise ErrorDotacion(str(exc)) from exc
    if Trabajador.objects.filter(rut=canonico).exists():
        raise ErrorDotacion(
            f"El RUT {canonico} ya está registrado: es la misma persona."
        )

    with transaction.atomic():
        trabajador = Trabajador.objects.create(
            rut=canonico,
            nombre=nombre,
            cargo=cargo,
            creado_por=actor,
        )
        AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=centro,
            tipo=TipoAsignacion.ALTA,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="alta_trabajador",
            entidad="Trabajador",
            identificador=trabajador.rut,
            descripcion=(
                f"Dio de alta a {trabajador.nombre} ({trabajador.rut}) como "
                f"{trabajador.cargo} en {centro.nombre}, sin validar. "
                f"Motivo: {motivo}"
            ),
            canal=canal,
            contexto=ContextoBitacora.para_trabajador(trabajador, centro),
        )
    return trabajador


def validar_trabajador(
    *,
    trabajador: Trabajador,
    actor: User,
    canal: str = "web",
) -> ValidacionTrabajador:
    exigir_prevencionista(actor, "validar un trabajador")
    if trabajador.esta_validado():
        raise ErrorDotacion("El trabajador ya fue validado.")

    with transaction.atomic():
        validacion = ValidacionTrabajador.objects.create(
            trabajador=trabajador,
            validado_por=actor,
        )
        registrar_evento(
            actor=actor,
            accion="validar_trabajador",
            entidad="Trabajador",
            identificador=trabajador.rut,
            descripcion=(
                f"Incorporó a {trabajador.nombre} ({trabajador.rut}) a la "
                "dotación validada."
            ),
            canal=canal,
            contexto=ContextoBitacora.para_trabajador(
                trabajador,
                trabajador.centro_costo_actual,
            ),
        )
    return validacion


def trasladar_trabajador(
    *,
    trabajador: Trabajador,
    centro: CentroCosto,
    motivo: str,
    actor: User,
    canal: str = "web",
) -> AsignacionTrabajador:
    """Mueve a la persona sin perder nada de lo que acreditó donde estaba."""
    exigir_prevencionista(actor, "trasladar un trabajador")
    if trabajador.esta_de_baja():
        raise ErrorDotacion(
            "El trabajador está dado de baja: no se puede trasladar."
        )
    origen = trabajador.centro_costo_actual
    if origen is not None and origen.pk == centro.pk:
        raise ErrorDotacion(
            f"{trabajador.nombre} ya pertenece a {centro.nombre}."
        )

    with transaction.atomic():
        asignacion = AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=centro,
            tipo=TipoAsignacion.TRASLADO,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="trasladar_trabajador",
            entidad="Trabajador",
            identificador=trabajador.rut,
            descripcion=(
                f"Trasladó a {trabajador.nombre} ({trabajador.rut}) "
                f"{'desde ' + origen.nombre + ' ' if origen else ''}"
                f"a {centro.nombre}. Motivo: {motivo}"
            ),
            canal=canal,
            contexto=ContextoBitacora.para_trabajador(trabajador, centro),
        )
    return asignacion


def dar_de_baja_trabajador(
    *,
    trabajador: Trabajador,
    motivo: str,
    actor: User,
    canal: str = "web",
) -> AsignacionTrabajador:
    """Cierra la pertenencia con motivo. No borra: la historia se conserva."""
    exigir_prevencionista(actor, "dar de baja un trabajador")
    if trabajador.esta_de_baja():
        raise ErrorDotacion("El trabajador ya está dado de baja.")
    origen = trabajador.centro_costo_actual

    with transaction.atomic():
        asignacion = AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=None,
            tipo=TipoAsignacion.BAJA,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="baja_trabajador",
            entidad="Trabajador",
            identificador=trabajador.rut,
            descripcion=(
                f"Dio de baja a {trabajador.nombre} ({trabajador.rut}); su "
                f"historia queda consultable. Motivo: {motivo}"
            ),
            canal=canal,
            contexto=ContextoBitacora.para_trabajador(trabajador, origen),
        )
    return asignacion


# --- consultas sobre la dotación -----------------------------------------


@dataclass(frozen=True)
class Dotacion:
    """Quién estaba dónde, y validado, en una fecha: resuelto de una sola vez.

    Preguntarlo persona por persona cuesta una consulta por persona y por
    obligación. A la escala del piloto —129 trabajadores por 14 obligaciones—
    eso son miles de consultas para pintar una sola bandeja, así que la
    dotación de una fecha se lee entera y se comparte.
    """

    en_fecha: date | None
    centros: dict[int, CentroCosto]
    validados: frozenset[int]
    personas: dict[int, Trabajador]

    def centro_de(self, trabajador: Trabajador) -> CentroCosto | None:
        """Dónde estaba, o None si estaba de baja o aún no existía."""
        return self.centros.get(trabajador.pk)

    def esta_validado(self, trabajador: Trabajador) -> bool:
        return trabajador.pk in self.validados

    def produce_cumplimiento(self, trabajador: Trabajador) -> bool:
        """Un trabajador no validado o dado de baja no acredita nada."""
        return self.esta_validado(trabajador) and self.centro_de(trabajador) is not None

    def del_centro(
        self,
        centro: CentroCosto,
        *,
        solo_validados: bool = True,
    ) -> list[Trabajador]:
        dotacion = [
            trabajador
            for trabajador in self.personas.values()
            if self.centros.get(trabajador.pk) is not None
            and self.centros[trabajador.pk].pk == centro.pk
            and (not solo_validados or self.esta_validado(trabajador))
        ]
        return sorted(dotacion, key=lambda persona: (persona.nombre, persona.rut))


def leer_dotacion(*, en_fecha: date | None = None) -> Dotacion:
    """Lee de una vez a quién tenía cada centro de costo en esa fecha."""
    asignaciones = AsignacionTrabajador.objects.select_related(
        "trabajador__validacion",
        "centro_costo",
    )
    if en_fecha is not None:
        asignaciones = asignaciones.filter(ocurrido_en__lte=fin_del_dia(en_fecha))

    centros: dict[int, CentroCosto] = {}
    personas: dict[int, Trabajador] = {}
    validados: set[int] = set()
    vistos: set[int] = set()
    for asignacion in asignaciones.order_by("trabajador_id", "-ocurrido_en", "-pk"):
        if asignacion.trabajador_id in vistos:
            continue
        vistos.add(asignacion.trabajador_id)
        trabajador = asignacion.trabajador
        personas[trabajador.pk] = trabajador
        if trabajador.esta_validado(en_fecha=en_fecha):
            validados.add(trabajador.pk)
        if asignacion.tipo == TipoAsignacion.BAJA:
            continue
        if asignacion.centro_costo is not None:
            centros[trabajador.pk] = asignacion.centro_costo
    return Dotacion(
        en_fecha=en_fecha,
        centros=centros,
        validados=frozenset(validados),
        personas=personas,
    )


def dotacion_del_centro(
    centro: CentroCosto,
    *,
    en_fecha: date | None = None,
    solo_validados: bool = True,
) -> list[Trabajador]:
    """Quiénes pertenecían a ese centro de costo en esa fecha."""
    return leer_dotacion(en_fecha=en_fecha).del_centro(
        centro,
        solo_validados=solo_validados,
    )
