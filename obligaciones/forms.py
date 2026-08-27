from django import forms

from centros_costo.models import CentroCosto
from obligaciones.models import Periodicidad, TitularObligacion


class FormularioObligacion(forms.Form):
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
        help_text="Vacío significa todos los tipos.",
        widget=forms.CheckboxSelectMultiple,
    )
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)

class FormularioCierre(forms.Form):
    fecha_cierre = forms.DateField(
        label="Fecha de cierre",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)
