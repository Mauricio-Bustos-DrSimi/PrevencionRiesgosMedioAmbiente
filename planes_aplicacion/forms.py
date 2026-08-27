from typing import Any, cast

from django import forms

from obligaciones.models import Obligacion


class MotivoAplicabilidadForm(forms.Form):
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea)


class CambioAplicabilidadForm(MotivoAplicabilidadForm):
    obligacion = forms.ModelChoiceField(
        label="Obligación",
        queryset=Obligacion.objects.none(),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        campo = cast(forms.ModelChoiceField, self.fields["obligacion"])
        campo.queryset = Obligacion.objects.all()
