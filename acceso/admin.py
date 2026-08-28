from typing import Any, cast

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.http import HttpRequest

from bitacora.registro import ContextoBitacora, registrar_evento


def _datos_usuario(usuario: User) -> str:
    grupos = ", ".join(usuario.groups.order_by("name").values_list("name", flat=True))
    return (
        f'usuario "{usuario.username}", activo "{usuario.is_active}", '
        f'personal "{usuario.is_staff}", Sysadmin "{usuario.is_superuser}", '
        f'grupos "{grupos or "—"}"'
    )


def _datos_grupo(grupo: Group) -> str:
    permisos = ", ".join(
        grupo.permissions.order_by("content_type__app_label", "codename").values_list(
            "codename",
            flat=True,
        )
    )
    return f'grupo "{grupo.name}", permisos "{permisos or "—"}"'


class RegistroAdminInmutableMixin:
    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UsuarioTrazableAdmin(RegistroAdminInmutableMixin, UserAdmin):
    def save_model(
        self,
        request: HttpRequest,
        obj: User,
        form: Any,
        change: bool,
    ) -> None:
        anterior = _datos_usuario(User.objects.get(pk=obj.pk)) if change else None
        setattr(obj, "_datos_anteriores_bitacora", anterior)
        super().save_model(request, obj, form, change)

    def save_related(
        self,
        request: HttpRequest,
        form: Any,
        formsets: list[Any],
        change: bool,
    ) -> None:
        super().save_related(request, form, formsets, change)
        usuario = cast(User, form.instance)
        anterior = getattr(usuario, "_datos_anteriores_bitacora", None)
        accion = "Modificó" if change else "Creó"
        descripcion = (
            f"Datos anteriores: {anterior}. Datos nuevos: {_datos_usuario(usuario)}."
            if anterior is not None
            else f"Datos: {_datos_usuario(usuario)}."
        )
        registrar_evento(
            actor=request.user,
            accion=accion,
            entidad="Cuenta local",
            identificador=usuario.username,
            descripcion=descripcion,
            canal="Panel administrativo",
            contexto=ContextoBitacora.general(),
        )


@admin.register(Group)
class GrupoTrazableAdmin(RegistroAdminInmutableMixin, GroupAdmin):
    def save_model(
        self,
        request: HttpRequest,
        obj: Group,
        form: Any,
        change: bool,
    ) -> None:
        anterior = _datos_grupo(Group.objects.get(pk=obj.pk)) if change else None
        setattr(obj, "_datos_anteriores_bitacora", anterior)
        super().save_model(request, obj, form, change)

    def save_related(
        self,
        request: HttpRequest,
        form: Any,
        formsets: list[Any],
        change: bool,
    ) -> None:
        super().save_related(request, form, formsets, change)
        grupo = cast(Group, form.instance)
        anterior = getattr(grupo, "_datos_anteriores_bitacora", None)
        accion = "Modificó" if change else "Creó"
        descripcion = (
            f"Datos anteriores: {anterior}. Datos nuevos: {_datos_grupo(grupo)}."
            if anterior is not None
            else f"Datos: {_datos_grupo(grupo)}."
        )
        registrar_evento(
            actor=request.user,
            accion=accion,
            entidad="Grupo de acceso",
            identificador=grupo.name,
            descripcion=descripcion,
            canal="Panel administrativo",
            contexto=ContextoBitacora.general(),
        )
