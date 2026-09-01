from typing import Any, cast

from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from trabajadores.models import Trabajador


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
    # Se pide sin exigirlo en el formulario para que la falta la explique el
    # dominio —«una bodega no tiene licencia de conducir»— y no un «campo
    # obligatorio» que no dice nada.
    trabajador = forms.ModelChoiceField(
        label="Trabajador",
        queryset=Trabajador.objects.none(),
        required=False,
        empty_label="— Indica a quién acredita —",
    )

    def __init__(
        self,
        *args: Any,
        dotacion: QuerySet[Trabajador] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        campo = cast(forms.ModelChoiceField, self.fields["trabajador"])
        if dotacion is None:
            del self.fields["trabajador"]
        else:
            campo.queryset = dotacion

    def clean(self) -> dict[str, object]:
        datos = super().clean()
        if datos is None:
            return {}
        emision = datos.get("fecha_emision")
        vencimiento = datos.get("fecha_vencimiento")
        if emision and emision > timezone.localdate():
            self.add_error(
                "fecha_emision",
                "La fecha de emisión no puede ser futura.",
            )
        if emision and vencimiento and vencimiento <= emision:
            self.add_error(
                "fecha_vencimiento",
                "La fecha de vencimiento debe ser posterior a la emisión.",
            )
        return datos


class CorreccionEvidenciaForm(forms.Form):
    """Las fechas que Prevención lee en un documento que no las declaraba."""

    fecha_emision = forms.DateField(
        label="Fecha de emisión que dice el documento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vencimiento = forms.DateField(
        label="Fecha de vencimiento que dice el documento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo = forms.CharField(label="Motivo de la corrección", widget=forms.Textarea)


class ValidacionEvidenciaForm(forms.Form):
    """Validar, corrigiendo las fechas en el mismo envío si hace falta."""

    corregir_fechas = forms.BooleanField(
        label="Corregir las fechas leídas del documento",
        required=False,
    )
    fecha_emision = forms.DateField(
        label="Fecha de emisión que dice el documento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vencimiento = forms.DateField(
        label="Fecha de vencimiento que dice el documento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    motivo = forms.CharField(
        label="Motivo de la corrección",
        required=False,
        widget=forms.Textarea,
    )

    def clean(self) -> dict[str, object]:
        datos = super().clean()
        if datos is None:
            return {}
        if not datos.get("corregir_fechas"):
            return datos
        for campo, mensaje in (
            ("fecha_emision", "Indica la fecha de emisión que dice el documento."),
            (
                "fecha_vencimiento",
                "Indica la fecha de vencimiento que dice el documento.",
            ),
            ("motivo", "Explica por qué se corrige la fecha."),
        ):
            if not datos.get(campo):
                self.add_error(campo, mensaje)
        return datos
