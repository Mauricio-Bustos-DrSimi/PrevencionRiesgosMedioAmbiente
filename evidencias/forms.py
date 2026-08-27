from django import forms


class EvidenciaForm(forms.Form):
    emisor = forms.CharField(label="Emisor", max_length=255)
    fecha_emision = forms.DateField(
        label="Fecha de emisión",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vencimiento = forms.DateField(
        label="Fecha de vencimiento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    archivo = forms.FileField(label="Archivo de evidencia")

    def clean(self) -> dict[str, object]:
        datos = super().clean()
        if datos is None:
            return {}
        emision = datos.get("fecha_emision")
        vencimiento = datos.get("fecha_vencimiento")
        if emision and vencimiento and vencimiento <= emision:
            self.add_error(
                "fecha_vencimiento",
                "La fecha de vencimiento debe ser posterior a la emisión.",
            )
        return datos
