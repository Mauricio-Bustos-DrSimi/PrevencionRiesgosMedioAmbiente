from typing import Any

from django.db import migrations


def _identificador_numerico(identificador: str) -> int | None:
    try:
        return int(identificador)
    except ValueError:
        return None


def relacionar_eventos_existentes(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    EventoBitacora = apps.get_model("bitacora", "EventoBitacora")
    CentroCosto = apps.get_model("centros_costo", "CentroCosto")
    Obligacion = apps.get_model("obligaciones", "Obligacion")
    Evidencia = apps.get_model("evidencias", "Evidencia")
    CambioAplicabilidad = apps.get_model(
        "planes_aplicacion",
        "CambioAplicabilidad",
    )

    eventos = EventoBitacora.objects.filter(
        centro_costo__isnull=True,
        obligacion__isnull=True,
        evidencia__isnull=True,
    )
    for evento in eventos.iterator():
        entidad = evento.entidad.casefold()
        campos: list[str] = []
        if entidad == "centro de costo":
            centro = CentroCosto.objects.filter(
                codigo_contable=evento.identificador,
            ).first()
            if centro is not None:
                evento.centro_costo_id = centro.pk
                campos.append("centro_costo")
        elif entidad == "obligación":
            obligacion_pk = _identificador_numerico(evento.identificador)
            if obligacion_pk is not None and Obligacion.objects.filter(
                pk=obligacion_pk,
            ).exists():
                evento.obligacion_id = obligacion_pk
                campos.append("obligacion")
        elif entidad == "evidencia":
            evidencia_pk = _identificador_numerico(evento.identificador)
            evidencia = (
                Evidencia.objects.filter(pk=evidencia_pk).first()
                if evidencia_pk is not None
                else None
            )
            if evidencia is not None:
                evento.evidencia_id = evidencia.pk
                evento.centro_costo_id = evidencia.centro_costo_id
                evento.obligacion_id = evidencia.obligacion_id
                campos.extend(("evidencia", "centro_costo", "obligacion"))
        elif entidad == "plan de aplicación":
            centro_pk = _identificador_numerico(evento.identificador)
            if centro_pk is not None and CentroCosto.objects.filter(
                pk=centro_pk,
            ).exists():
                evento.centro_costo_id = centro_pk
                campos.append("centro_costo")
                aplica = {
                    "aplicar": True,
                    "declarar_no_aplica": False,
                }.get(evento.accion)
                if aplica is not None:
                    candidatos = CambioAplicabilidad.objects.filter(
                        centro_costo_id=centro_pk,
                        autor_id=evento.actor_id,
                        aplica=aplica,
                    )
                    cambio = min(
                        candidatos,
                        key=lambda candidato: abs(
                            (evento.ocurrido_en - candidato.ocurrido_en).total_seconds()
                        ),
                        default=None,
                    )
                    if cambio is not None and abs(
                        (evento.ocurrido_en - cambio.ocurrido_en).total_seconds()
                    ) <= 5:
                        evento.obligacion_id = cambio.obligacion_id
                        campos.append("obligacion")
        if campos:
            evento.save(update_fields=campos)


class Migration(migrations.Migration):
    dependencies = [
        ("bitacora", "0002_evento_relaciones_recorrido"),
        ("planes_aplicacion", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            relacionar_eventos_existentes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
