import django.db.models.deletion
from django.conf import settings
from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def crear_grupo_encargado(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    grupo = apps.get_model("auth", "Group")
    grupo.objects.get_or_create(name="Encargado")


def eliminar_grupo_encargado(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    grupo = apps.get_model("auth", "Group")
    grupo.objects.filter(name="Encargado").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("acceso", "0001_crear_grupo_prevencionista"),
        ("centros_costo", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AsignacionEncargadoCentro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("asignacion", "Asignación"), ("revocacion", "Revocación")], max_length=20)),
                ("motivo", models.TextField()),
                ("ocurrido_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("autor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_encargados_registradas", to=settings.AUTH_USER_MODEL)),
                ("centro_costo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_encargados", to="centros_costo.centrocosto")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones_como_encargado", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "asignación de Encargado a centro",
                "verbose_name_plural": "asignaciones de Encargados a centros",
                "ordering": ("-ocurrido_en", "-pk"),
                "indexes": [models.Index(fields=["usuario", "centro_costo", "-ocurrido_en"], name="acceso_enc_centro_hist_idx")],
            },
        ),
        migrations.RunPython(crear_grupo_encargado, eliminar_grupo_encargado),
    ]
