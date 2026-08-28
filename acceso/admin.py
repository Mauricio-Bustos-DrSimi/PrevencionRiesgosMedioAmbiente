from typing import Any, cast

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters

from bitacora.registro import ContextoBitacora, registrar_evento


def _datos_usuario(usuario: User) -> str:
    grupos = ", ".join(usuario.groups.order_by("name").values_list("name", flat=True))
    permisos = ", ".join(
        f"{aplicacion}.{codigo}"
        for aplicacion, codigo in usuario.user_permissions.order_by(
            "content_type__app_label",
            "codename",
        ).values_list("content_type__app_label", "codename")
    )
    return (
        f'usuario "{usuario.username}", nombres "{usuario.first_name}", '
        f'apellidos "{usuario.last_name}", correo "{usuario.email}", '
        f'activo "{usuario.is_active}", '
        f'personal "{usuario.is_staff}", Sysadmin "{usuario.is_superuser}", '
        f'grupos "{grupos or "—"}", permisos directos "{permisos or "—"}", '
        f'fecha de alta "{usuario.date_joined.isoformat()}"'
    )


def _datos_grupo(grupo: Group) -> str:
    permisos = ", ".join(
        f"{aplicacion}.{codigo}"
        for aplicacion, codigo in grupo.permissions.order_by(
            "content_type__app_label",
            "codename",
        ).values_list("content_type__app_label", "codename")
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

    @method_decorator(sensitive_post_parameters())
    def user_change_password(
        self,
        request: HttpRequest,
        id: str,
        form_url: str = "",
    ) -> HttpResponse:
        usuario = self.get_object(request, id)
        hash_anterior = usuario.password if usuario is not None else None
        respuesta = super().user_change_password(request, id, form_url)
        if request.method == "POST" and usuario is not None:
            usuario.refresh_from_db()
            if usuario.password != hash_anterior:
                accion = (
                    "Deshabilitó contraseña"
                    if not usuario.has_usable_password()
                    else "Cambió contraseña"
                )
                registrar_evento(
                    actor=request.user,
                    accion=accion,
                    entidad="Cuenta local",
                    identificador=usuario.username,
                    descripcion=(
                        f"{accion} para la cuenta local {usuario.username}; "
                        "el valor secreto no se conserva en la bitácora."
                    ),
                    canal="Panel administrativo",
                    contexto=ContextoBitacora.general(),
                )
        return respuesta


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
