from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


MENSAJE_INMUTABLE = "Las obligaciones y sus versiones no se pueden modificar ni eliminar."


class TitularObligacion(models.TextChoices):
    CENTRO_COSTO = "centro_costo", "Centro de costo"
    TRABAJADOR = "trabajador", "Trabajador"
    EXTERNO = "externo", "Externo"
    EMPRESA = "empresa", "Empresa"


class Periodicidad(models.TextChoices):
    ANUAL = "anual", "Anual"
    BIENAL = "bienal", "Bienal"
    POR_EVENTO = "por_evento", "Por evento"
    PERMANENTE = "permanente", "Permanente"


class TipoVersion(models.TextChoices):
    ALTA = "alta", "Alta"
    CORRECCION = "correccion", "Corrección"
    CIERRE = "cierre", "Cierre"


class RegistroInmutableQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


class Obligacion(models.Model):
    creada_en = models.DateTimeField(auto_now_add=True)

    objects = RegistroInmutableQuerySet.as_manager()

    class Meta:
        verbose_name = "obligación"
        verbose_name_plural = "obligaciones"

    @property
    def version_actual(self) -> "VersionObligacion":
        return self.versiones.latest("numero")

    @property
    def esta_vigente(self) -> bool:
        return self.version_actual.tipo_version != TipoVersion.CIERRE

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

    def __str__(self) -> str:
        return self.version_actual.nombre


class VersionObligacion(models.Model):
    obligacion = models.ForeignKey(
        Obligacion,
        on_delete=models.PROTECT,
        related_name="versiones",
    )
    numero = models.PositiveIntegerField()
    nombre = models.CharField(max_length=255)
    norma_origen = models.CharField("norma de origen", max_length=255)
    titular = models.CharField(max_length=30, choices=TitularObligacion.choices)
    periodicidad = models.CharField(max_length=30, choices=Periodicidad.choices)
    tipo_version = models.CharField(max_length=20, choices=TipoVersion.choices)
    fecha_cierre = models.DateField(null=True, blank=True)
    autor = models.ForeignKey[AbstractUser, AbstractUser](
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="versiones_obligacion_creadas",
    )
    motivo = models.TextField()
    creada_en = models.DateTimeField(auto_now_add=True)

    objects = RegistroInmutableQuerySet.as_manager()

    class Meta:
        ordering = ("numero",)
        constraints = [
            models.UniqueConstraint(
                fields=("obligacion", "numero"),
                name="obligacion_numero_version_unico",
            )
        ]
        verbose_name = "versión de obligación"
        verbose_name_plural = "versiones de obligación"

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

    def __str__(self) -> str:
        return f"{self.nombre} — versión {self.numero}"
