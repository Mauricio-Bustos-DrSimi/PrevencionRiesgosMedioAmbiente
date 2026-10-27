from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


EXAMENES_OCUPACIONALES_DEMO = (
    "Examen ocupacional de altura física",
    "Examen ocupacional de conductor clase D",
    "Examen ocupacional de operadores de maquinaria",
    "Examen ocupacional de conductor de vehículo liviano",
)


def clasificar_examenes_existentes(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    version = apps.get_model("obligaciones", "VersionObligacion")
    obligaciones = version._base_manager.filter(
        nombre__in=EXAMENES_OCUPACIONALES_DEMO
    ).values_list("obligacion_id", flat=True)
    version._base_manager.filter(obligacion_id__in=obligaciones).update(
        clasificacion_evidencia="salud_ocupacional"
    )


def revertir_clasificacion(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    version = apps.get_model("obligaciones", "VersionObligacion")
    obligaciones = version._base_manager.filter(
        nombre__in=EXAMENES_OCUPACIONALES_DEMO
    ).values_list("obligacion_id", flat=True)
    version._base_manager.filter(obligacion_id__in=obligaciones).update(
        clasificacion_evidencia="general"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("obligaciones", "0003_versionobligacion_cargos_sugeridos"),
    ]

    operations = [
        migrations.AddField(
            model_name="versionobligacion",
            name="clasificacion_evidencia",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("salud_ocupacional", "Salud ocupacional"),
                ],
                default="general",
                max_length=30,
                verbose_name="clasificación de la evidencia",
            ),
        ),
        migrations.RunPython(
            clasificar_examenes_existentes,
            revertir_clasificacion,
        ),
    ]
