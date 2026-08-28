import hashlib
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from bitacora.registro import registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, Periodicidad
from planes_aplicacion.services import estado_actual

from .models import EstadoEvidencia, Evidencia, ValidacionEvidencia


class ErrorCargaEvidencia(Exception):
    """Indica que el archivo o el registro no pudo completarse."""


class ErrorValidacionEvidencia(Exception):
    """Indica que una evidencia no admite otra validación."""


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
    if not actor.groups.filter(name="Prevencionista").exists():
        raise PermissionDenied("Solo un Prevencionista puede validar evidencia.")
    if evidencia.estado == EstadoEvidencia.VALIDADA:
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


def _sumar_anos(fecha: date, anos: int) -> date:
    try:
        return fecha.replace(year=fecha.year + anos)
    except ValueError:
        return fecha.replace(year=fecha.year + anos, month=2, day=28)


def fecha_fin_vigencia(evidencia: Evidencia) -> date:
    periodicidad = Periodicidad(evidencia.periodicidad)
    if periodicidad == Periodicidad.PERMANENTE:
        return date.max
    if periodicidad == Periodicidad.ANUAL:
        limite_periodico = _sumar_anos(evidencia.fecha_emision, 1)
        return min(evidencia.fecha_vencimiento, limite_periodico)
    if periodicidad == Periodicidad.BIENAL:
        limite_periodico = _sumar_anos(evidencia.fecha_emision, 2)
        return min(evidencia.fecha_vencimiento, limite_periodico)
    return evidencia.fecha_vencimiento


def evidencia_esta_vigente(evidencia: Evidencia, *, en_fecha: date) -> bool:
    return evidencia.fecha_emision <= en_fecha <= fecha_fin_vigencia(evidencia)
