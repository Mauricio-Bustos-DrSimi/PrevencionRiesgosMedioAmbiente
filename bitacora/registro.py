from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User

from bitacora.models import EventoBitacora
from obligaciones.models import ClasificacionEvidencia

if TYPE_CHECKING:
    from centros_costo.models import CentroCosto
    from evidencias.models import Evidencia
    from obligaciones.models import Obligacion
    from trabajadores.models import Trabajador


@dataclass(frozen=True)
class ContextoBitacora:
    centro_costo: "CentroCosto | None" = None
    obligacion: "Obligacion | None" = None
    evidencia: "Evidencia | None" = None
    trabajador: "Trabajador | None" = None

    @classmethod
    def general(cls) -> "ContextoBitacora":
        return cls()

    @classmethod
    def para_centro(cls, centro: "CentroCosto") -> "ContextoBitacora":
        return cls(centro_costo=centro)

    @classmethod
    def para_obligacion(cls, obligacion: "Obligacion") -> "ContextoBitacora":
        return cls(obligacion=obligacion)

    @classmethod
    def para_plan(
        cls,
        centro: "CentroCosto",
        obligacion: "Obligacion | None" = None,
    ) -> "ContextoBitacora":
        return cls(centro_costo=centro, obligacion=obligacion)

    @classmethod
    def para_evidencia(cls, evidencia: "Evidencia") -> "ContextoBitacora":
        return cls(
            centro_costo=evidencia.centro_costo,
            obligacion=evidencia.obligacion,
            evidencia=evidencia,
            trabajador=evidencia.trabajador,
        )

    @classmethod
    def para_trabajador(
        cls,
        trabajador: "Trabajador",
        centro: "CentroCosto | None" = None,
        obligacion: "Obligacion | None" = None,
    ) -> "ContextoBitacora":
        return cls(centro_costo=centro, obligacion=obligacion, trabajador=trabajador)


def registrar_evento(
    *,
    actor: AbstractBaseUser | AnonymousUser,
    accion: str,
    entidad: str,
    identificador: str,
    descripcion: str,
    canal: str,
    contexto: ContextoBitacora,
) -> EventoBitacora:
    """Agrega un acto trazable a la bitácora inmutable del dominio."""
    if not actor.is_authenticated:
        raise ValueError("La bitácora requiere un usuario autenticado como actor.")

    es_salud_ocupacional = False
    if contexto.evidencia is not None:
        es_salud_ocupacional = (
            contexto.evidencia.version_obligacion.clasificacion_evidencia
            == ClasificacionEvidencia.SALUD_OCUPACIONAL
        )
    elif contexto.obligacion is not None and contexto.obligacion.versiones.exists():
        es_salud_ocupacional = contexto.obligacion.versiones.filter(
            clasificacion_evidencia=ClasificacionEvidencia.SALUD_OCUPACIONAL
        ).exists()
    if es_salud_ocupacional:
        descripcion = "Acto relacionado con salud ocupacional registrado."
        if contexto.evidencia is not None:
            identificador = str(contexto.evidencia.pk)
        elif contexto.obligacion is not None:
            identificador = str(contexto.obligacion.pk)

    return EventoBitacora.objects.create(
        actor=cast(User, actor),
        accion=accion,
        entidad=entidad,
        identificador=identificador,
        descripcion=descripcion,
        canal=canal,
        centro_costo=contexto.centro_costo,
        obligacion=contexto.obligacion,
        evidencia=contexto.evidencia,
        trabajador=contexto.trabajador,
    )
