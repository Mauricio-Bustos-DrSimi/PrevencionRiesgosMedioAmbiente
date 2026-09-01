from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


GRUPO_PREVENCIONISTA = "Prevencionista"
Parametros = ParamSpec("Parametros")
Respuesta = TypeVar("Respuesta", bound=HttpResponse)


def es_operador_mvp(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    if not usuario.is_authenticated:
        return False
    actor = cast(User, usuario)
    return actor.is_superuser or actor.groups.filter(
        name=GRUPO_PREVENCIONISTA,
    ).exists()


def exigir_prevencionista(actor: User, accion: str) -> None:
    """Los actos que solo le tocan a Prevención se hacen valer en el servidor.

    Ocultar un botón prueba la pantalla; lo que tiene que quedar demostrado es
    que el acto se rechaza aunque se envíe el formulario directamente.
    """
    if not actor.groups.filter(name=GRUPO_PREVENCIONISTA).exists():
        raise PermissionDenied(f"Solo un Prevencionista puede {accion}.")


def requiere_operador_mvp(
    vista: Callable[Parametros, Respuesta],
) -> Callable[Parametros, Respuesta]:
    @login_required
    @wraps(vista)
    def protegida(
        *args: Parametros.args,
        **kwargs: Parametros.kwargs,
    ) -> Respuesta:
        request = cast(HttpRequest, args[0])
        if not es_operador_mvp(request.user):
            raise PermissionDenied
        return vista(*args, **kwargs)

    return protegida
