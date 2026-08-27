from django.db import models


class CentroCosto(models.Model):
    class Tipo(models.TextChoices):
        FARMACIA = "farmacia", "Farmacia"
        CENTRO_ADMINISTRATIVO = (
            "centro_administrativo",
            "Centro administrativo",
        )
        BODEGA = "bodega", "Bodega"

    codigo_contable = models.CharField(
        "código contable oficial",
        max_length=50,
        unique=True,
    )
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    cve_unidad = models.CharField(
        "CveUnidad",
        max_length=50,
        blank=True,
        default="",
        help_text="Referencia cruzada opcional; no reemplaza al código contable oficial.",
    )
    es_franquicia = models.BooleanField(
        "es franquicia",
        default=False,
        help_text="Las franquicias quedan fuera del alcance operativo del sistema.",
    )

    class Meta:
        ordering = ("codigo_contable",)
        verbose_name = "centro de costo"
        verbose_name_plural = "centros de costo"

    def __str__(self) -> str:
        return f"{self.codigo_contable} — {self.nombre}"
