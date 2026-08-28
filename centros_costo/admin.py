from django.contrib import admin
from django.http import HttpRequest

from bitacora.registro import registrar_evento

from .models import CentroCosto


@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_contable",
        "nombre",
        "tipo",
        "cve_unidad",
        "es_franquicia",
    )
    list_filter = ("tipo", "es_franquicia")
    search_fields = ("codigo_contable", "nombre", "cve_unidad")

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: CentroCosto | None = None,
    ) -> bool:
        return False

    def save_model(
        self,
        request: HttpRequest,
        obj: CentroCosto,
        form: object,
        change: bool,
    ) -> None:
        super().save_model(request, obj, form, change)
        accion = "Modificó" if change else "Creó"
        registrar_evento(
            actor=request.user,
            accion=accion,
            entidad="Centro de costo",
            identificador=obj.codigo_contable,
            descripcion=f"{accion} el centro de costo {obj.nombre}.",
            canal="Panel administrativo",
            centro_costo=obj,
        )
