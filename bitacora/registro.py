from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User

from bitacora.models import EventoBitacora

if TYPE_CHECKING:
    from centros_costo.models import CentroCosto
    from evidencias.models import Evidencia
    from obligaciones.models import Obligacion


def registrar_evento(
    *,
    actor: AbstractBaseUser | AnonymousUser,
    accion: str,
    entidad: str,
    identificador: str,
    descripcion: str,
    canal: str,
    centro_costo: "CentroCosto | None" = None,
    obligacion: "Obligacion | None" = None,
    evidencia: "Evidencia | None" = None,
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
        centro_costo=centro_costo,
        obligacion=obligacion,
        evidencia=evidencia,
    )
