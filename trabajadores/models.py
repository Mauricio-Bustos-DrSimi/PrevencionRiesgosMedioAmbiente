from datetime import date
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto
from configuracion.tiempo import fin_del_dia

from .rut import RutInvalido, normalizar_rut


MENSAJE_INMUTABLE = (
    "Los actos sobre la dotación no se pueden modificar ni eliminar: la baja "
    "de un trabajador es un cierre con motivo, no un borrado."
)


class RegistroDotacionQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_INMUTABLE)


class RegistroDotacionInmutable(models.Model):
    objects = RegistroDotacionQuerySet.as_manager()

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


class TipoAsignacion(models.TextChoices):
    ALTA = "alta", "Alta"
    TRASLADO = "traslado", "Traslado"
    BAJA = "baja", "Baja"


class Trabajador(models.Model):
    """Persona contratada, titular de sus propias obligaciones.

    Se identifica por su RUT y no por su nombre. El cargo es un atributo que
    alimenta la sugerencia de su plan; cambiarlo no altera por sí solo lo que
    ya se confirmó.
    """

    rut = models.CharField("RUT", max_length=12, unique=True)
    nombre = models.CharField(max_length=200)
    cargo = models.CharField(max_length=120)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trabajadores_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("nombre", "rut")
        verbose_name = "trabajador"
        verbose_name_plural = "trabajadores"

    def __str__(self) -> str:
        return f"{self.rut} — {self.nombre}"

    def clean(self) -> None:
        super().clean()
        try:
            self.rut = normalizar_rut(self.rut)
        except RutInvalido as exc:
            raise ValidationError({"rut": str(exc)}) from exc

    def save(self, *args: Any, **kwargs: Any) -> None:
        try:
            self.rut = normalizar_rut(self.rut)
        except RutInvalido as exc:
            raise ValidationError(str(exc)) from exc
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        del using, keep_parents
        raise ValidationError(MENSAJE_INMUTABLE)

    # --- lo que se deriva de la historia ---------------------------------

    def asignacion_vigente(
        self,
        *,
        en_fecha: date | None = None,
    ) -> "AsignacionTrabajador | None":
        asignaciones = self.asignaciones.all()
        if en_fecha is not None:
            asignaciones = asignaciones.filter(
                ocurrido_en__lte=fin_del_dia(en_fecha),
            )
        return asignaciones.order_by("-ocurrido_en", "-pk").first()

    def centro_costo_en(self, en_fecha: date | None = None) -> CentroCosto | None:
        """A qué centro de costo pertenecía en esa fecha."""
        asignacion = self.asignacion_vigente(en_fecha=en_fecha)
        if asignacion is None or asignacion.tipo == TipoAsignacion.BAJA:
            return None
        return asignacion.centro_costo

    @property
    def centro_costo_actual(self) -> CentroCosto | None:
        return self.centro_costo_en()

    def esta_de_baja(self, *, en_fecha: date | None = None) -> bool:
        asignacion = self.asignacion_vigente(en_fecha=en_fecha)
        return asignacion is not None and asignacion.tipo == TipoAsignacion.BAJA

    def esta_validado(self, *, en_fecha: date | None = None) -> bool:
        validacion = getattr(self, "validacion", None)
        if validacion is None:
            return False
        return en_fecha is None or validacion.validado_en <= fin_del_dia(en_fecha)

    def produce_cumplimiento(self, *, en_fecha: date | None = None) -> bool:
        """Un trabajador no validado o dado de baja no acredita nada."""
        return (
            self.esta_validado(en_fecha=en_fecha)
            and self.centro_costo_en(en_fecha) is not None
        )


class ValidacionTrabajador(RegistroDotacionInmutable):
    """Prevención incorpora formalmente a la persona a la dotación."""

    trabajador = models.OneToOneField(
        Trabajador,
        on_delete=models.PROTECT,
        related_name="validacion",
    )
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trabajadores_validados",
    )
    validado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-validado_en", "-pk")
        verbose_name = "validación de trabajador"
        verbose_name_plural = "validaciones de trabajador"


class AsignacionTrabajador(RegistroDotacionInmutable):
    """Dónde está una persona, registrado como historia y no como campo.

    Sin esta historia, reconstruir el estado agregado de un centro de costo a
    una fecha pasada usaría la dotación de hoy para juzgar el pasado.
    """

    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.PROTECT,
        related_name="asignaciones",
    )
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.PROTECT,
        related_name="asignaciones_trabajador",
        null=True,
        blank=True,
        help_text="Vacío solo en una baja: la persona deja de estar en un centro.",
    )
    tipo = models.CharField(max_length=20, choices=TipoAsignacion.choices)
    motivo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asignaciones_realizadas",
    )
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-ocurrido_en", "-pk")
        verbose_name = "asignación de trabajador"
        verbose_name_plural = "asignaciones de trabajador"

    def __str__(self) -> str:
        destino = self.centro_costo.nombre if self.centro_costo else "sin centro"
        return f"{self.trabajador.rut} — {self.get_tipo_display()} — {destino}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.tipo == TipoAsignacion.BAJA:
            if self.centro_costo_id is not None:
                raise ValidationError(
                    "Una baja cierra la pertenencia: no indica centro de costo."
                )
        elif self.centro_costo_id is None:
            raise ValidationError(
                "Un alta o un traslado deben indicar el centro de costo."
            )
        super().save(*args, **kwargs)
