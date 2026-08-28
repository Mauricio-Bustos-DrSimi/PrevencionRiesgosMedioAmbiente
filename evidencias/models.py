from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, Periodicidad, VersionObligacion


MENSAJE_INMUTABLE = "Las evidencias no se pueden modificar ni eliminar."


class EstadoEvidencia(models.TextChoices):
    PENDIENTE_VALIDACION = "pendiente_validacion", "Pendiente de validación"
    VALIDADA = "validada", "Validada"


class RegistroEvidenciaInmutableQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


def ruta_evidencia(instance: "Evidencia", nombre: str) -> str:
    del instance
    return f"evidencias/{nombre}"


class RegistroEvidenciaInmutable(models.Model):
    objects = RegistroEvidenciaInmutableQuerySet.as_manager()

    class Meta:
        abstract = True

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


class Evidencia(RegistroEvidenciaInmutable):
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
    version_obligacion = models.ForeignKey(
        VersionObligacion,
        on_delete=models.PROTECT,
        related_name="evidencias",
    )
    archivo = models.FileField(upload_to=ruta_evidencia)
    hash_sha256 = models.CharField(max_length=64)
    emisor = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    cargada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidencias_cargadas",
    )
    cargada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-cargada_en", "-pk")
        verbose_name = "evidencia"
        verbose_name_plural = "evidencias"

    @property
    def estado_validacion(self) -> EstadoEvidencia:
        if ValidacionEvidencia.objects.filter(evidencia=self).exists():
            return EstadoEvidencia.VALIDADA
        return EstadoEvidencia.PENDIENTE_VALIDACION

    @property
    def nombre_obligacion(self) -> str:
        return self.version_obligacion.nombre

    @property
    def periodicidad(self) -> Periodicidad:
        return Periodicidad(self.version_obligacion.periodicidad)

    @property
    def periodicidad_mostrada(self) -> str:
        return self.periodicidad.label


class ValidacionEvidencia(RegistroEvidenciaInmutable):
    evidencia = models.OneToOneField(
        Evidencia,
        on_delete=models.PROTECT,
        related_name="validacion",
    )
    validada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidencias_validadas",
    )
    validada_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-validada_en", "-pk")
        verbose_name = "validación de evidencia"
        verbose_name_plural = "validaciones de evidencia"
