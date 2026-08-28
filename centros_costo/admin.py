from django.contrib import admin
from django.http import HttpRequest

from bitacora.registro import ContextoBitacora, registrar_evento

from .models import CentroCosto


def _datos_trazables(centro: CentroCosto) -> str:
    cve_unidad = centro.cve_unidad or "—"
    franquicia = "sí" if centro.es_franquicia else "no"
    return (
        f'código contable "{centro.codigo_contable}", '
        f'nombre "{centro.nombre}", tipo "{centro.get_tipo_display()}", '
        f'CveUnidad "{cve_unidad}", franquicia "{franquicia}"'
    )


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
        anterior = CentroCosto.objects.get(pk=obj.pk) if change else None
        super().save_model(request, obj, form, change)
        accion = "Modificó" if change else "Creó"
        if anterior is None:
            descripcion = (
                f"Creó el centro de costo {obj.nombre}. "
                f"Datos: {_datos_trazables(obj)}."
            )
        else:
            descripcion = (
                f"Modificó el centro de costo {obj.nombre}. "
                f"Datos anteriores: {_datos_trazables(anterior)}. "
                f"Datos nuevos: {_datos_trazables(obj)}."
            )
        registrar_evento(
            actor=request.user,
            accion=accion,
            entidad="Centro de costo",
            identificador=obj.codigo_contable,
            descripcion=descripcion,
            canal="Panel administrativo",
            contexto=ContextoBitacora.para_centro(obj),
        )
