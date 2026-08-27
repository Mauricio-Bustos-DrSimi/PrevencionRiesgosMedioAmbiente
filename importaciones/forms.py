from django import forms


class ImportacionForm(forms.Form):
    TIPO_CENTROS = "centros_costo"
    TIPO_OBLIGACIONES = "obligaciones"

    tipo = forms.ChoiceField(
        label="Tipo de datos",
        choices=(
            (TIPO_CENTROS, "Centros de costo"),
            (TIPO_OBLIGACIONES, "Obligaciones"),
        ),
    )
    archivo = forms.FileField(label="Archivo CSV")
