from django.contrib import admin
from django.http import HttpRequest

from .models import AsignacionTrabajador, Trabajador, ValidacionTrabajador


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre", "cargo", "centro_costo_actual", "creado_en")
    search_fields = ("rut", "nombre", "cargo")
    readonly_fields = ("creado_por", "creado_en")

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Trabajador | None = None,
    ) -> bool:
        # La baja de un trabajador es un cierre con motivo, no un borrado.
        return False


@admin.register(AsignacionTrabajador)
class AsignacionTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "tipo", "centro_costo", "autor", "ocurrido_en")
    list_filter = ("tipo",)

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: AsignacionTrabajador | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: AsignacionTrabajador | None = None,
    ) -> bool:
        return False


@admin.register(ValidacionTrabajador)
class ValidacionTrabajadorAdmin(admin.ModelAdmin):
    list_display = ("trabajador", "validado_por", "validado_en")

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ValidacionTrabajador | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ValidacionTrabajador | None = None,
    ) -> bool:
        return False
