from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, QuerySet, Subquery
from django.http import HttpRequest, HttpResponse

from centros_costo.models import CentroCosto
from obligaciones.models import ClasificacionEvidencia

from .models import AsignacionEncargadoCentro, TipoAsignacionEncargado

if TYPE_CHECKING:
    from evidencias.models import Evidencia
    from obligaciones.models import VersionObligacion


GRUPO_PREVENCIONISTA = "Prevencionista"
GRUPO_ENCARGADO = "Encargado"
Parametros = ParamSpec("Parametros")
Respuesta = TypeVar("Respuesta", bound=HttpResponse)


def es_administrador(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return bool(usuario.is_authenticated and cast(User, usuario).is_superuser)


def es_prevencionista(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return bool(
        usuario.is_authenticated
        and cast(User, usuario).groups.filter(name=GRUPO_PREVENCIONISTA).exists()
    )


def es_encargado(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return bool(
        usuario.is_authenticated
        and cast(User, usuario).groups.filter(name=GRUPO_ENCARGADO).exists()
    )


def es_operador_mvp(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return es_administrador(usuario) or es_prevencionista(usuario) or es_encargado(usuario)


def puede_modificar_mvp(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return es_administrador(usuario) or es_prevencionista(usuario)


def centros_visibles_para(
    usuario: AbstractBaseUser | AnonymousUser,
) -> QuerySet[CentroCosto]:
    centros = CentroCosto.objects.filter(es_franquicia=False)
    if es_administrador(usuario) or es_prevencionista(usuario):
        return centros
    if not es_encargado(usuario):
        return centros.none()
    actor = cast(User, usuario)
    ultimo_tipo = (
        AsignacionEncargadoCentro.objects.filter(
            usuario=actor,
            centro_costo=OuterRef("pk"),
        )
        .order_by("-ocurrido_en", "-pk")
        .values("tipo")[:1]
    )
    return centros.annotate(_ultimo_acceso=Subquery(ultimo_tipo)).filter(
        _ultimo_acceso=TipoAsignacionEncargado.ASIGNACION
    )


def puede_acceder_centro(
    usuario: AbstractBaseUser | AnonymousUser,
    centro: CentroCosto,
) -> bool:
    return centros_visibles_para(usuario).filter(pk=centro.pk).exists()


def exigir_acceso_centro(
    usuario: AbstractBaseUser | AnonymousUser,
    centro: CentroCosto,
) -> None:
    if not puede_acceder_centro(usuario, centro):
        raise PermissionDenied("No tiene permiso para consultar este centro.")


def exigir_modificador_mvp(usuario: AbstractBaseUser | AnonymousUser) -> None:
    if not puede_modificar_mvp(usuario):
        raise PermissionDenied("No tiene permiso para modificar información.")


def exigir_prevencionista(actor: User, accion: str) -> None:
    """Los actos que solo le tocan a Prevención se hacen valer en el servidor.

    Ocultar un botón prueba la pantalla; lo que tiene que quedar demostrado es
    que el acto se rechaza aunque se envíe el formulario directamente.
    """
    if not puede_modificar_mvp(actor):
        raise PermissionDenied(f"Solo Prevención o Administración puede {accion}.")


def exigir_acceso_evidencia(
    actor: AbstractBaseUser | AnonymousUser,
    evidencia: "Evidencia",
) -> None:
    """Conserva los documentos de salud dentro de su perímetro explícito."""
    if not puede_acceder_centro(actor, evidencia.centro_costo) or not puede_acceder_version_evidencia(
        actor,
        evidencia.version_obligacion,
    ):
        raise PermissionDenied("No tiene permiso para consultar esta evidencia.")


def puede_acceder_salud_ocupacional(
    actor: AbstractBaseUser | AnonymousUser,
) -> bool:
    """La salud ocupacional queda limitada a los dos roles acordados."""
    if actor.is_authenticated:
        return es_administrador(actor) or es_prevencionista(actor)
    return False


def puede_acceder_version_evidencia(
    actor: AbstractBaseUser | AnonymousUser,
    version: "VersionObligacion | None",
) -> bool:
    if version is None:
        return True
    return (
        version.clasificacion_evidencia != ClasificacionEvidencia.SALUD_OCUPACIONAL
        or puede_acceder_salud_ocupacional(actor)
    )


def exigir_acceso_version_evidencia(
    actor: AbstractBaseUser | AnonymousUser,
    version: "VersionObligacion",
) -> None:
    if not puede_acceder_version_evidencia(actor, version):
        raise PermissionDenied("No tiene permiso para consultar esta evidencia.")


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


def requiere_modificador_mvp(
    vista: Callable[Parametros, Respuesta],
) -> Callable[Parametros, Respuesta]:
    @login_required
    @wraps(vista)
    def protegida(
        *args: Parametros.args,
        **kwargs: Parametros.kwargs,
    ) -> Respuesta:
        request = cast(HttpRequest, args[0])
        exigir_modificador_mvp(request.user)
        return vista(*args, **kwargs)

    return protegida
