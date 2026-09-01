from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TitularObligacion

from .rut import FORMA_CANONICA, RutInvalido, normalizar_rut


def _centros_operables() -> QuerySet[CentroCosto]:
    return CentroCosto.objects.filter(es_franquicia=False)


def _obligaciones_del_trabajador() -> QuerySet[Obligacion]:
    """Solo lo que puede recaer sobre una persona.

    Ofrecer una obligación del centro de costo dejaría armar un plan que
    después ninguna evidencia puede acreditar: el titular no calza.
    """
    vigentes = [
        obligacion.pk
        for obligacion in Obligacion.objects.prefetch_related("versiones")
        if obligacion.esta_vigente
        and obligacion.version_actual.titular == TitularObligacion.TRABAJADOR
    ]
    return Obligacion.objects.filter(pk__in=vigentes)


class SujetoConCentroForm(forms.Form):
    """Base de los formularios que eligen un centro de costo operable."""

    etiqueta_centro = "Centro de costo"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = cast(forms.ModelChoiceField, self.fields["centro_costo"])
        campo.queryset = _centros_operables()
        campo.label = self.etiqueta_centro


class TrabajadorForm(SujetoConCentroForm):
    rut = forms.CharField(
        label="RUT",
        max_length=15,
        help_text=f"Se guarda {FORMA_CANONICA}.",
    )
    nombre = forms.CharField(label="Nombre", max_length=200)
    cargo = forms.CharField(label="Cargo", max_length=120)
    centro_costo = forms.ModelChoiceField(queryset=CentroCosto.objects.none())
    motivo = forms.CharField(label="Motivo del alta", widget=forms.Textarea)

    def clean_rut(self) -> str:
        try:
            return normalizar_rut(self.cleaned_data["rut"])
        except RutInvalido as exc:
            raise forms.ValidationError(str(exc)) from exc


class MotivoForm(forms.Form):
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)


class TrasladoForm(SujetoConCentroForm):
    etiqueta_centro = "Centro de costo de destino"

    centro_costo = forms.ModelChoiceField(queryset=CentroCosto.objects.none())
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)


class AplicabilidadTrabajadorForm(MotivoForm):
    obligacion = forms.ModelChoiceField(
        label="Obligación",
        queryset=Obligacion.objects.none(),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = cast(forms.ModelChoiceField, self.fields["obligacion"])
        campo.queryset = _obligaciones_del_trabajador()
