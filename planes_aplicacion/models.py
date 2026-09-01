from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion
from trabajadores.models import Trabajador


MENSAJE_INMUTABLE = (
    "Los cambios de aplicabilidad no se pueden modificar ni eliminar."
)

MENSAJE_SUJETO = (
    "Un cambio de aplicabilidad recae sobre un centro de costo o sobre un "
    "trabajador, nunca sobre los dos ni sobre ninguno."
)


class CambioAplicabilidadQuerySet(models.QuerySet["CambioAplicabilidad"]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


class CambioAplicabilidad(models.Model):
    """El plan de aplicación de un sujeto: un centro de costo o una persona.

    La aplicabilidad no se hereda del tipo de centro ni del cargo: se confirma
    individualmente, y cada confirmación queda con autor, fecha y motivo.
    """

    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.PROTECT,
        related_name="cambios_aplicabilidad",
        null=True,
        blank=True,
    )
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.PROTECT,
        related_name="cambios_aplicabilidad",
        null=True,
        blank=True,
    )
    obligacion = models.ForeignKey(
        Obligacion,
        on_delete=models.PROTECT,
        related_name="cambios_aplicabilidad",
    )
    aplica = models.BooleanField()
    motivo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cambios_aplicabilidad_realizados",
    )
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = CambioAplicabilidadQuerySet.as_manager()

    class Meta:
        ordering = ("-ocurrido_en", "-pk")
        verbose_name = "cambio de aplicabilidad"
        verbose_name_plural = "cambios de aplicabilidad"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        centro_costo__isnull=False,
                        trabajador__isnull=True,
                    )
                    | models.Q(
                        centro_costo__isnull=True,
                        trabajador__isnull=False,
                    )
                ),
                name="cambio_aplicabilidad_un_solo_sujeto",
            )
        ]

    def __str__(self) -> str:
        sujeto = self.trabajador or self.centro_costo
        return f"{sujeto} — {'Aplica' if self.aplica else 'No aplica'}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError(MENSAJE_INMUTABLE)
        if (self.centro_costo_id is None) == (self.trabajador_id is None):
            raise ValidationError(MENSAJE_SUJETO)
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        del using, keep_parents
        raise ValidationError(MENSAJE_INMUTABLE)
