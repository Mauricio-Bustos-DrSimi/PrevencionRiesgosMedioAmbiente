from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion


MENSAJE_INMUTABLE = "Las evidencias no se pueden modificar ni eliminar."


class EstadoEvidencia(models.TextChoices):
    PENDIENTE_VALIDACION = "pendiente_validacion", "Pendiente de validación"
    VALIDADA = "validada", "Validada"


class EvidenciaQuerySet(models.QuerySet["Evidencia"]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


def ruta_evidencia(instance: "Evidencia", nombre: str) -> str:
    del instance
    return f"evidencias/{nombre}"


class Evidencia(models.Model):
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.PROTECT,
        related_name="evidencias",
    )
    obligacion = models.ForeignKey(
        Obligacion,
        on_delete=models.PROTECT,
        related_name="evidencias",
    )
    archivo = models.FileField(upload_to=ruta_evidencia)
    hash_sha256 = models.CharField(max_length=64)
    emisor = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(
        max_length=30,
        choices=EstadoEvidencia.choices,
        default=EstadoEvidencia.PENDIENTE_VALIDACION,
    )
    cargada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidencias_cargadas",
    )
    cargada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = EvidenciaQuerySet.as_manager()

    class Meta:
        ordering = ("-cargada_en", "-pk")
        verbose_name = "evidencia"
        verbose_name_plural = "evidencias"

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
