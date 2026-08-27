from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


MENSAJE_INMUTABLE = "Los eventos de la bitácora no se pueden modificar ni eliminar."


class EventoBitacoraQuerySet(models.QuerySet["EventoBitacora"]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


class EventoBitacora(models.Model):
    actor = models.ForeignKey[User, User](
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_bitacora",
        verbose_name="actor",
    )
    accion = models.CharField("acción", max_length=100)
    entidad = models.CharField(max_length=100)
    identificador = models.CharField(max_length=255)
    descripcion = models.TextField("descripción")
    canal = models.CharField(max_length=100)
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = EventoBitacoraQuerySet.as_manager()

    class Meta:
        ordering = ("-ocurrido_en", "-pk")
        verbose_name = "evento de bitácora"
        verbose_name_plural = "eventos de bitácora"

    def __str__(self) -> str:
        return f"{self.ocurrido_en:%Y-%m-%d %H:%M:%S} — {self.accion} — {self.entidad} {self.identificador}"

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
