from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.apps.registry import Apps


NOMBRE_GRUPO = "Prevencionista"


def crear_grupo_prevencionista(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    modelo_grupo = apps.get_model("auth", "Group")
    modelo_grupo.objects.get_or_create(name=NOMBRE_GRUPO)


def eliminar_grupo_prevencionista(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    modelo_grupo = apps.get_model("auth", "Group")
    modelo_grupo.objects.filter(name=NOMBRE_GRUPO).delete()


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [
        migrations.RunPython(
            crear_grupo_prevencionista,
            eliminar_grupo_prevencionista,
        )
    ]
