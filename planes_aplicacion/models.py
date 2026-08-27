from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion


MENSAJE_INMUTABLE = (
    "Los cambios de aplicabilidad no se pueden modificar ni eliminar."
)


class CambioAplicabilidadQuerySet(models.QuerySet["CambioAplicabilidad"]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


class CambioAplicabilidad(models.Model):
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.PROTECT,
        related_name="cambios_aplicabilidad",
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

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError(MENSAJE_INMUTABLE)
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        del using, keep_parents
        raise ValidationError(MENSAJE_INMUTABLE)
