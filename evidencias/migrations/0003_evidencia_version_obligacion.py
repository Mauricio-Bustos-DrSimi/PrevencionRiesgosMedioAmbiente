from typing import Any

import django.db.models.deletion
from django.db import migrations, models


def asociar_version_de_obligacion(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    Evidencia = apps.get_model("evidencias", "Evidencia")
    VersionObligacion = apps.get_model("obligaciones", "VersionObligacion")

    for evidencia in Evidencia.objects.all().iterator():
        version = (
            VersionObligacion.objects.filter(obligacion_id=evidencia.obligacion_id)
            .order_by("-numero")
            .first()
        )
        if version is None:
            raise RuntimeError(
                "La evidencia no tiene una versión de obligación disponible "
                "para preservar su contexto."
            )
        Evidencia.objects.filter(pk=evidencia.pk).update(
            version_obligacion_id=version.pk,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("evidencias", "0002_remove_evidencia_estado_validacionevidencia"),
        ("obligaciones", "0002_versionobligacion_tipos_centro"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidencia",
            name="version_obligacion",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="evidencias",
                to="obligaciones.versionobligacion",
            ),
        ),
        migrations.RunPython(
            asociar_version_de_obligacion,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="evidencia",
            name="version_obligacion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="evidencias",
                to="obligaciones.versionobligacion",
            ),
        ),
    ]
