from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import Q


def sanitizar_eventos_salud_ocupacional(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    VersionObligacion = apps.get_model("obligaciones", "VersionObligacion")
    Evidencia = apps.get_model("evidencias", "Evidencia")
    EventoBitacora = apps.get_model("bitacora", "EventoBitacora")

    obligaciones = VersionObligacion._base_manager.filter(
        clasificacion_evidencia="salud_ocupacional"
    ).values_list("obligacion_id", flat=True)
    evidencias = Evidencia._base_manager.filter(
        version_obligacion__clasificacion_evidencia="salud_ocupacional"
    ).values_list("pk", flat=True)
    ids_evidencias = list(evidencias)
    ids_texto = [str(pk) for pk in ids_evidencias]
    eventos = EventoBitacora._base_manager.filter(
        Q(obligacion_id__in=obligaciones)
        | Q(evidencia_id__in=ids_evidencias)
        | Q(
            evidencia__isnull=True,
            entidad__iexact="Evidencia",
            identificador__in=ids_texto,
        )
    ).only("pk", "evidencia_id", "obligacion_id")

    for evento in eventos.iterator():
        if evento.evidencia_id is not None:
            identificador = str(evento.evidencia_id)
        elif evento.obligacion_id is not None:
            identificador = str(evento.obligacion_id)
        else:
            identificador = evento.identificador
        EventoBitacora._base_manager.filter(pk=evento.pk).update(
            identificador=identificador,
            descripcion="Acto relacionado con salud ocupacional registrado.",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("bitacora", "0003_eventobitacora_trabajador"),
        ("evidencias", "0003_evidencia_version_obligacion"),
        ("obligaciones", "0004_versionobligacion_clasificacion_evidencia"),
    ]

    operations = [
        migrations.RunPython(
            sanitizar_eventos_salud_ocupacional,
            migrations.RunPython.noop,
        ),
    ]
