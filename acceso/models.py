from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from centros_costo.models import CentroCosto


MENSAJE_ASIGNACION_INMUTABLE = (
    "Las asignaciones de acceso no se pueden modificar ni eliminar."
)


class TipoAsignacionEncargado(models.TextChoices):
    ASIGNACION = "asignacion", "Asignación"
    REVOCACION = "revocacion", "Revocación"


class AsignacionEncargadoCentroQuerySet(models.QuerySet["AsignacionEncargadoCentro"]):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise ValidationError(MENSAJE_ASIGNACION_INMUTABLE)

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(MENSAJE_ASIGNACION_INMUTABLE)


class AsignacionEncargadoCentro(models.Model):
    objects = AsignacionEncargadoCentroQuerySet.as_manager()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asignaciones_como_encargado",
    )
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.PROTECT,
        related_name="asignaciones_encargados",
    )
    tipo = models.CharField(max_length=20, choices=TipoAsignacionEncargado.choices)
    motivo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asignaciones_encargados_registradas",
    )
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-ocurrido_en", "-pk")
        verbose_name = "asignación de Encargado a centro"
        verbose_name_plural = "asignaciones de Encargados a centros"
        indexes = [
            models.Index(
                fields=("usuario", "centro_costo", "-ocurrido_en"),
                name="acceso_enc_centro_hist_idx",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.usuario.username} — {self.centro_costo.codigo_contable} — "
            f"{self.get_tipo_display()}"
        )

    def clean(self) -> None:
        super().clean()
        if self.usuario_id is not None:
            if not self.usuario.is_active:
                raise ValidationError({"usuario": "El usuario debe estar activo."})
            if not self.usuario.groups.filter(name="Encargado").exists():
                raise ValidationError(
                    {"usuario": "El usuario debe pertenecer al rol Encargado."}
                )
        if self.autor_id is not None and not self.autor.is_superuser:
            raise ValidationError(
                {"autor": "Solo un Administrador puede registrar asignaciones."}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError(MENSAJE_ASIGNACION_INMUTABLE)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        del using, keep_parents
        raise ValidationError(MENSAJE_ASIGNACION_INMUTABLE)
