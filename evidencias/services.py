import hashlib
from datetime import date
from enum import StrEnum
from typing import Any

from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from bitacora.registro import registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, Periodicidad
from planes_aplicacion.services import estado_actual

from .models import Evidencia, ValidacionEvidencia


class ErrorCargaEvidencia(Exception):
    """Indica que el archivo o el registro no pudo completarse."""


class ErrorValidacionEvidencia(Exception):
    """Indica que una evidencia no admite otra validación."""


class EstadoCumplimiento(StrEnum):
    NO_APLICA = "No aplica"
    SIN_EVIDENCIA = "Sin evidencia"
    PENDIENTE_VALIDACION = "Pendiente de validación"
    VIGENTE = "Vigente"
    VENCIDO = "Vencido"


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


def validar_evidencia(
    *,
    evidencia: Evidencia,
    actor: User,
) -> ValidacionEvidencia:
    if ValidacionEvidencia.objects.filter(evidencia=evidencia).exists():
        raise ErrorValidacionEvidencia("La evidencia ya fue validada.")

    with transaction.atomic():
        validacion = ValidacionEvidencia.objects.create(
            evidencia=evidencia,
            validada_por=actor,
        )
        registrar_evento(
            actor=actor,
            accion="validar_evidencia",
            entidad="Evidencia",
            identificador=str(evidencia.pk),
            descripcion=(
                f"Validó evidencia para {evidencia.obligacion}; confirmó "
                "su correspondencia y sus fechas."
            ),
            canal="web",
        )
    return validacion


def evidencia_esta_vigente(evidencia: Evidencia, *, en_fecha: date) -> bool:
    periodicidad = Periodicidad(evidencia.obligacion.version_actual.periodicidad)
    if periodicidad == Periodicidad.PERMANENTE:
        return evidencia.fecha_emision <= en_fecha
    return evidencia.fecha_emision <= en_fecha <= evidencia.fecha_vencimiento


def estado_cumplimiento(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    en_fecha: date | None = None,
) -> EstadoCumplimiento:
    cambio = estado_actual(centro, obligacion)
    if cambio is None or not cambio.aplica:
        return EstadoCumplimiento.NO_APLICA

    evidencias = list(
        Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
        )
        .select_related("obligacion")
        .order_by("-cargada_en", "-pk")
    )
    if not evidencias:
        return EstadoCumplimiento.SIN_EVIDENCIA

    mas_reciente = evidencias[0]
    if not ValidacionEvidencia.objects.filter(evidencia=mas_reciente).exists():
        return EstadoCumplimiento.PENDIENTE_VALIDACION

    fecha_consulta = en_fecha or timezone.localdate()
    for evidencia in evidencias:
        if (
            ValidacionEvidencia.objects.filter(evidencia=evidencia).exists()
            and evidencia_esta_vigente(evidencia, en_fecha=fecha_consulta)
        ):
            return EstadoCumplimiento.VIGENTE
    return EstadoCumplimiento.VENCIDO
