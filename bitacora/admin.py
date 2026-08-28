from django.contrib import admin
from django.http import HttpRequest

from bitacora.models import EventoBitacora


@admin.register(EventoBitacora)
class EventoBitacoraAdmin(admin.ModelAdmin):
    list_display = (
        "ocurrido_en",
        "actor",
        "accion",
        "entidad",
        "identificador",
        "descripcion",
        "canal",
    )
    list_filter = ("accion", "entidad", "canal")
    search_fields = (
        "actor__username",
        "accion",
        "entidad",
        "identificador",
        "descripcion",
        "canal",
    )
    readonly_fields = (
        "ocurrido_en",
        "actor",
        "accion",
        "entidad",
        "identificador",
        "descripcion",
        "canal",
    )
    ordering = ("-ocurrido_en", "-pk")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: EventoBitacora | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: EventoBitacora | None = None,
    ) -> bool:
        return False
