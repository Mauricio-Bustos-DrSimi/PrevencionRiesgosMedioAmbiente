from typing import cast

from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpRequest

from bitacora.registro import registrar_evento

from .models import CambioAplicabilidad


@admin.register(CambioAplicabilidad)
class CambioAplicabilidadAdmin(admin.ModelAdmin):
    list_display = (
        "ocurrido_en",
        "centro_costo",
        "obligacion",
        "aplica",
        "autor",
    )
    list_filter = ("aplica", "centro_costo")
    search_fields = (
        "centro_costo__codigo_contable",
        "centro_costo__nombre",
        "obligacion__versiones__nombre",
        "motivo",
        "autor__username",
    )
    readonly_fields = ("autor", "ocurrido_en")

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: CambioAplicabilidad | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: CambioAplicabilidad | None = None,
    ) -> bool:
        return False

    def save_model(
        self,
        request: HttpRequest,
        obj: CambioAplicabilidad,
        form: object,
        change: bool,
    ) -> None:
        if change:
            return
        obj.autor = cast(User, request.user)
        super().save_model(request, obj, form, change)
        registrar_evento(
            actor=request.user,
            accion="aplicar" if obj.aplica else "declarar_no_aplica",
            entidad="plan de aplicación",
            identificador=str(obj.centro_costo_id),
            descripcion=f"Actualizó la aplicabilidad de {obj.obligacion}.",
            canal="Panel administrativo",
            centro_costo=obj.centro_costo,
            obligacion=obj.obligacion,
        )
