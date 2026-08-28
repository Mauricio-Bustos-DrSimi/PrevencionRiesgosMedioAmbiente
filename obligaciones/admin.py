from typing import cast

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpRequest

from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto

from .models import (
    Obligacion,
    Periodicidad,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)


class AltaObligacionAdminForm(forms.ModelForm):
    nombre = forms.CharField(label="Obligación", max_length=255)
    norma_origen = forms.CharField(label="Norma de origen", max_length=255)
    titular = forms.ChoiceField(
        label="Titular de obligación",
        choices=((TitularObligacion.CENTRO_COSTO, "Centro de costo"),),
    )
    periodicidad = forms.ChoiceField(
        label="Periodicidad",
        choices=Periodicidad.choices,
    )
    tipos_centro = forms.MultipleChoiceField(
        label="Tipos de centro sugeridos",
        choices=CentroCosto.Tipo.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)

    class Meta:
        model = Obligacion
        fields: tuple[()] = ()


@admin.register(Obligacion)
class ObligacionAdmin(admin.ModelAdmin):
    form = AltaObligacionAdminForm
    fields = (
        "nombre",
        "norma_origen",
        "titular",
        "periodicidad",
        "tipos_centro",
        "motivo",
    )
    list_display = (
        "nombre_actual",
        "norma_actual",
        "periodicidad_actual",
        "creada_en",
    )
    list_display_links = None
    search_fields = ("versiones__nombre", "versiones__norma_origen")

    @admin.display(description="Obligación")
    def nombre_actual(self, obj: Obligacion) -> str:
        return obj.version_actual.nombre

    @admin.display(description="Norma de origen")
    def norma_actual(self, obj: Obligacion) -> str:
        return obj.version_actual.norma_origen

    @admin.display(description="Periodicidad")
    def periodicidad_actual(self, obj: Obligacion) -> str:
        return obj.version_actual.get_periodicidad_display()

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Obligacion | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Obligacion | None = None,
    ) -> bool:
        return False

    def save_model(
        self,
        request: HttpRequest,
        obj: Obligacion,
        form: AltaObligacionAdminForm,
        change: bool,
    ) -> None:
        if change:
            return
        super().save_model(request, obj, form, change)
        actor = cast(User, request.user)
        version = VersionObligacion.objects.create(
            obligacion=obj,
            numero=1,
            nombre=form.cleaned_data["nombre"],
            norma_origen=form.cleaned_data["norma_origen"],
            titular=form.cleaned_data["titular"],
            periodicidad=form.cleaned_data["periodicidad"],
            tipos_centro=form.cleaned_data["tipos_centro"],
            tipo_version=TipoVersion.ALTA,
            autor=actor,
            motivo=form.cleaned_data["motivo"],
        )
        registrar_evento(
            actor=actor,
            accion="alta",
            entidad="obligación",
            identificador=str(obj.pk),
            descripcion=f"Se registró {version.nombre}.",
            canal="Panel administrativo",
            contexto=ContextoBitacora.para_obligacion(obj),
        )
