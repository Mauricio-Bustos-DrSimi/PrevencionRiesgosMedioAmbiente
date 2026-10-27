from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from centros_costo.models import CentroCosto
from obligaciones.models import (
    ClasificacionEvidencia,
    Obligacion,
    Periodicidad,
    TitularObligacion,
    VersionObligacion,
)
from trabajadores.models import Trabajador


MENSAJE_INMUTABLE = "Las evidencias no se pueden modificar ni eliminar."

MENSAJE_FALTA_TRABAJADOR = (
    "Esta obligación es del trabajador: la evidencia tiene que indicar a qué "
    "persona acredita. Una instalación no tiene licencia de conducir."
)
MENSAJE_SOBRA_TRABAJADOR = (
    "Esta obligación es del centro de costo: la evidencia no puede atribuirse "
    "a una persona."
)
MENSAJE_TITULAR_NO_IMPLEMENTADO = (
    "El titular {titular} todavía no se puede acreditar en el sistema: los "
    "externos y las obligaciones de empresa son pasos posteriores."
)
MENSAJE_TRABAJADOR_AJENO = (
    "{trabajador} no pertenece a {centro}: la dotación y la evidencia no "
    "pueden contradecirse."
)
MENSAJE_TRABAJADOR_AJENO_SALUD = (
    "La persona seleccionada no pertenece al centro de costo indicado: la "
    "dotación y la evidencia no pueden contradecirse."
)


def exigir_titular_coherente(
    *,
    version: VersionObligacion,
    centro: CentroCosto,
    trabajador: "Trabajador | None",
) -> None:
    """La evidencia pertenece a un titular, y el titular lo fija el catálogo.

    El centro de costo dejó de ser el titular único y pasó a ser el contexto:
    sigue estando siempre, pero ya no responde por lo que es de una persona
    (ADR 0004).

    La pertenencia se comprueba **al momento de cargar**, no contra la fecha
    de emisión del documento: una licencia de conducir obtenida en 2019 es
    evidencia válida de quien entró a la empresa en 2024. Lo que no puede
    ocurrir es archivarla en un centro de costo al que la persona no pertenece.
    """
    titular = TitularObligacion(version.titular)
    if titular == TitularObligacion.TRABAJADOR:
        if trabajador is None:
            raise ValidationError(MENSAJE_FALTA_TRABAJADOR)
        if trabajador.centro_costo_en(timezone.localdate()) != centro:
            if (
                version.clasificacion_evidencia
                == ClasificacionEvidencia.SALUD_OCUPACIONAL
            ):
                raise ValidationError(MENSAJE_TRABAJADOR_AJENO_SALUD)
            raise ValidationError(
                MENSAJE_TRABAJADOR_AJENO.format(
                    trabajador=trabajador.nombre,
                    centro=centro.nombre,
                )
            )
        return
    if titular == TitularObligacion.CENTRO_COSTO:
        if trabajador is not None:
            raise ValidationError(MENSAJE_SOBRA_TRABAJADOR)
        return
    raise ValidationError(
        MENSAJE_TITULAR_NO_IMPLEMENTADO.format(titular=titular.label.lower())
    )


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
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidencias",
        help_text=(
            "Obligatorio cuando la obligación es del trabajador; vacío cuando "
            "es del centro de costo."
        ),
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

    @property
    def titular(self) -> TitularObligacion:
        return TitularObligacion(self.version_obligacion.titular)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.version_obligacion.obligacion_id != self.obligacion_id:
            raise ValidationError(
                "La versión de obligación debe pertenecer a la obligación "
                "asociada a la evidencia."
            )
        if self._state.adding:
            exigir_titular_coherente(
                version=self.version_obligacion,
                centro=self.centro_costo,
                trabajador=self.trabajador,
            )
        super().save(*args, **kwargs)


class CorreccionEvidencia(RegistroEvidenciaInmutable):
    """Lo que Prevención leyó en el documento cuando el sistema no pudo.

    No toca la evidencia: el archivo es el mismo y su hash sigue siendo el que
    se calculó al cargarlo. Enmienda lo que el sistema leyó del documento, no
    el documento, y por eso es un acto distinto de cargar una evidencia nueva.
    """

    evidencia = models.ForeignKey(
        Evidencia,
        on_delete=models.PROTECT,
        related_name="correcciones",
    )
    fecha_emision = models.DateField("fecha de emisión verdadera")
    fecha_vencimiento = models.DateField("fecha de vencimiento verdadera")
    motivo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="correcciones_evidencia",
    )
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-ocurrido_en", "-pk")
        verbose_name = "corrección de evidencia"
        verbose_name_plural = "correcciones de evidencia"

    def __str__(self) -> str:
        return (
            f"Corrección de la evidencia {self.evidencia_id}: "
            f"{self.fecha_emision} — {self.fecha_vencimiento}"
        )


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
