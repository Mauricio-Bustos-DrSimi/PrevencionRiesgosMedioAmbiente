import hashlib
from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from bitacora.registro import registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion
from planes_aplicacion.services import estado_actual

from .models import EstadoEvidencia, Evidencia


class ErrorCargaEvidencia(Exception):
    """Indica que el archivo o el registro no pudo completarse."""


def cargar_evidencia(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    actor: User,
    archivo: UploadedFile,
    emisor: str,
    fecha_emision: date,
    fecha_vencimiento: date,
) -> Evidencia:
    cambio = estado_actual(centro, obligacion)
    if cambio is None or not cambio.aplica:
        raise ErrorCargaEvidencia("No aplica: no se puede cargar esta evidencia.")

    digest = hashlib.sha256()
    for bloque in archivo.chunks():
        digest.update(bloque)
    archivo.seek(0)
    evidencia: Evidencia | None = None
    try:
        with transaction.atomic():
            evidencia = Evidencia(
                centro_costo=centro,
                obligacion=obligacion,
                hash_sha256=digest.hexdigest(),
                emisor=emisor,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                estado=EstadoEvidencia.PENDIENTE_VALIDACION,
                cargada_por=actor,
            )
            evidencia.archivo.save(archivo.name, archivo, save=False)
            evidencia.save()
            registrar_evento(
                actor=actor,
                accion="cargar_evidencia",
                entidad="Evidencia",
                identificador=str(evidencia.pk),
                descripcion=f"Cargó evidencia para {obligacion}.",
                canal="web",
            )
    except Exception as exc:
        if evidencia is not None and evidencia.archivo.name:
            evidencia.archivo.storage.delete(evidencia.archivo.name)
        raise ErrorCargaEvidencia(
            "No se pudo almacenar la evidencia; no se registró ninguna evidencia parcial."
        ) from exc
    return evidencia
