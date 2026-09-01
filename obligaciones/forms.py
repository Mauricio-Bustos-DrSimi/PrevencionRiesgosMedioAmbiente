from django import forms

from centros_costo.models import CentroCosto
from obligaciones.models import Periodicidad, TitularObligacion, cargos_escritos


class FormularioObligacion(forms.Form):
    nombre = forms.CharField(label="Obligación", max_length=255)
    norma_origen = forms.CharField(label="Norma de origen", max_length=255)
    titular = forms.ChoiceField(
        label="Titular de obligación",
        # Externo y empresa son pasos posteriores de la secuencia: se omiten
        # en vez de ofrecerse y fallar después al cargar la evidencia.
        choices=(
            (TitularObligacion.CENTRO_COSTO, "Centro de costo"),
            (TitularObligacion.TRABAJADOR, "Trabajador"),
        ),
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
    cargos_sugeridos = forms.CharField(
        label="Cargos sugeridos",
        required=False,
        help_text="Uno por línea; vacío significa todos los cargos.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)

    def clean_cargos_sugeridos(self) -> list[str]:
        return cargos_escritos(self.cleaned_data.get("cargos_sugeridos", ""))


class FormularioCierre(forms.Form):
    fecha_cierre = forms.DateField(
        label="Fecha de cierre",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)
