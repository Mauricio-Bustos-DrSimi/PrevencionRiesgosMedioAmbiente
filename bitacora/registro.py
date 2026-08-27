from typing import cast

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User

from bitacora.models import EventoBitacora


def registrar_evento(
    *,
    actor: AbstractBaseUser | AnonymousUser,
    accion: str,
    entidad: str,
    identificador: str,
    descripcion: str,
    canal: str,
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
    )
