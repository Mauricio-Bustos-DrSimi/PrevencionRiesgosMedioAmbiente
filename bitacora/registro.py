from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User

from bitacora.models import EventoBitacora

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
