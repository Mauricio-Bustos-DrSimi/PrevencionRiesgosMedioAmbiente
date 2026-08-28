import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, Periodicidad, VersionObligacion
from planes_aplicacion.models import CambioAplicabilidad
from planes_aplicacion.services import estado_actual

from .models import EstadoEvidencia, Evidencia, ValidacionEvidencia


class ErrorCargaEvidencia(Exception):
    """Indica que el archivo o el registro no pudo completarse."""


class ErrorValidacionEvidencia(Exception):
    """Indica que una evidencia no admite otra validación."""


class EstadoCumplimiento(StrEnum):
    VIGENTE = "Vigente"
    POR_VENCER = "Por vencer"
    VENCIDO = "Vencido"
    PENDIENTE_VALIDACION = "Pendiente de validación"
    SIN_EVIDENCIA = "Sin evidencia"
    NO_APLICA = "No aplica"


@dataclass(frozen=True)
class CasoCumplimiento:
    centro: CentroCosto
    obligacion: Obligacion
    estado: EstadoCumplimiento
    evidencia: Evidencia | None
    fecha_fin: date | None
    version_obligacion: VersionObligacion | None = None

    @property
    def nombre_obligacion(self) -> str:
        if self.version_obligacion is not None:
            return self.version_obligacion.nombre
        return str(self.obligacion)


@dataclass(frozen=True)
class ResultadoIntegridad:
    hash_registrado: str
    hash_calculado: str | None
    coincide: bool
    error: str | None = None


def verificar_integridad_archivo(evidencia: Evidencia) -> ResultadoIntegridad:
    digest = hashlib.sha256()
    try:
        with evidencia.archivo.open("rb") as archivo:
            for bloque in archivo.chunks():
                digest.update(bloque)
    except OSError:
        return ResultadoIntegridad(
            hash_registrado=evidencia.hash_sha256,
            hash_calculado=None,
            coincide=False,
            error="No se pudo abrir el archivo almacenado para verificarlo.",
        )
    hash_calculado = digest.hexdigest()
    return ResultadoIntegridad(
        hash_registrado=evidencia.hash_sha256,
        hash_calculado=hash_calculado,
        coincide=hash_calculado == evidencia.hash_sha256,
    )


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
                version_obligacion=obligacion.version_actual,
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
                contexto=ContextoBitacora.para_evidencia(evidencia),
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
    if evidencia.estado_validacion == EstadoEvidencia.VALIDADA:
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
                f"Validó evidencia para {evidencia.nombre_obligacion} "
                f"(versión {evidencia.version_obligacion.numero}); confirmó "
                "su correspondencia y sus fechas."
            ),
            canal="web",
            contexto=ContextoBitacora.para_evidencia(evidencia),
        )
    return validacion


def _sumar_anos(fecha: date, anos: int) -> date:
    try:
        return fecha.replace(year=fecha.year + anos)
    except ValueError:
        return fecha.replace(year=fecha.year + anos, month=2, day=28)


def fecha_fin_vigencia(evidencia: Evidencia) -> date:
    periodicidad = evidencia.periodicidad
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


def estado_de_evidencia_validada(
    evidencia: Evidencia,
    *,
    en_fecha: date,
) -> EstadoCumplimiento:
    fin = fecha_fin_vigencia(evidencia)
    if en_fecha < evidencia.fecha_emision:
        return EstadoCumplimiento.SIN_EVIDENCIA
    if en_fecha > fin:
        return EstadoCumplimiento.VENCIDO
    if en_fecha >= fin - timedelta(days=settings.DIAS_POR_VENCER):
        return EstadoCumplimiento.POR_VENCER
    return EstadoCumplimiento.VIGENTE


def estado_de_evidencia(
    evidencia: Evidencia,
    *,
    en_fecha: date,
) -> EstadoCumplimiento:
    estado_vigencia = estado_de_evidencia_validada(
        evidencia,
        en_fecha=en_fecha,
    )
    if estado_vigencia == EstadoCumplimiento.SIN_EVIDENCIA:
        return estado_vigencia
    validacion = getattr(evidencia, "validacion", None)
    if validacion is None or timezone.localdate(validacion.validada_en) > en_fecha:
        return EstadoCumplimiento.PENDIENTE_VALIDACION
    return estado_vigencia


def _fin_del_dia(fecha: date) -> datetime:
    return timezone.make_aware(datetime.combine(fecha, time.max))


def _version_en_fecha(
    obligacion: Obligacion,
    *,
    en_fecha: date,
) -> VersionObligacion | None:
    return (
        obligacion.versiones.filter(creada_en__lte=_fin_del_dia(en_fecha))
        .order_by("-numero")
        .first()
    )


def _evidencia_relevante(
    evidencias: list[Evidencia],
    *,
    en_fecha: date,
) -> Evidencia | None:
    for evidencia in evidencias:
        if evidencia.fecha_emision <= en_fecha:
            return evidencia
    return min(
        evidencias,
        key=lambda evidencia: (
            evidencia.fecha_emision,
            evidencia.cargada_en,
            evidencia.pk,
        ),
        default=None,
    )


def caso_de_cumplimiento(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    en_fecha: date,
) -> CasoCumplimiento | None:
    cambio = estado_actual(centro, obligacion, hasta=en_fecha)
    if cambio is None:
        return None
    version = _version_en_fecha(obligacion, en_fecha=en_fecha)
    if not cambio.aplica:
        return CasoCumplimiento(
            centro=centro,
            obligacion=obligacion,
            estado=EstadoCumplimiento.NO_APLICA,
            evidencia=None,
            fecha_fin=None,
            version_obligacion=version,
        )

    evidencias = list(
        Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
            cargada_en__lte=_fin_del_dia(en_fecha),
        ).select_related("version_obligacion", "validacion")
    )
    evidencia = _evidencia_relevante(evidencias, en_fecha=en_fecha)
    if evidencia is None:
        estado = EstadoCumplimiento.SIN_EVIDENCIA
        fecha_fin = None
    else:
        estado = estado_de_evidencia(evidencia, en_fecha=en_fecha)
        fecha_fin = (
            fecha_fin_vigencia(evidencia)
            if estado
            in {
                EstadoCumplimiento.VIGENTE,
                EstadoCumplimiento.POR_VENCER,
                EstadoCumplimiento.VENCIDO,
            }
            else None
        )
    return CasoCumplimiento(
        centro=centro,
        obligacion=obligacion,
        estado=estado,
        evidencia=evidencia,
        fecha_fin=fecha_fin,
        version_obligacion=version,
    )


def casos_de_cumplimiento(*, en_fecha: date) -> list[CasoCumplimiento]:
    cambios_actuales: dict[tuple[int, int], CambioAplicabilidad] = {}
    for cambio in CambioAplicabilidad.objects.filter(
        centro_costo__es_franquicia=False,
    ).select_related("centro_costo", "obligacion").order_by(
        "centro_costo_id",
        "obligacion_id",
        "-ocurrido_en",
        "-pk",
    ):
        clave = (cambio.centro_costo_id, cambio.obligacion_id)
        cambios_actuales.setdefault(clave, cambio)

    casos: list[CasoCumplimiento] = []
    for cambio in cambios_actuales.values():
        if not cambio.obligacion.esta_vigente:
            continue
        if not cambio.aplica:
            casos.append(
                CasoCumplimiento(
                    centro=cambio.centro_costo,
                    obligacion=cambio.obligacion,
                    estado=EstadoCumplimiento.NO_APLICA,
                    evidencia=None,
                    fecha_fin=None,
                    version_obligacion=_version_en_fecha(
                        cambio.obligacion,
                        en_fecha=en_fecha,
                    ),
                )
            )
            continue
        evidencias = list(
            Evidencia.objects.filter(
                centro_costo=cambio.centro_costo,
                obligacion=cambio.obligacion,
                cargada_en__lte=_fin_del_dia(en_fecha),
            )
            .select_related("version_obligacion", "validacion")
        )
        evidencia = _evidencia_relevante(evidencias, en_fecha=en_fecha)
        if evidencia is None:
            estado = EstadoCumplimiento.SIN_EVIDENCIA
            fecha_fin = None
        else:
            estado = estado_de_evidencia(evidencia, en_fecha=en_fecha)
            fecha_fin = (
                fecha_fin_vigencia(evidencia)
                if estado
                in {
                    EstadoCumplimiento.VIGENTE,
                    EstadoCumplimiento.POR_VENCER,
                    EstadoCumplimiento.VENCIDO,
                }
                else None
            )
        casos.append(
            CasoCumplimiento(
                centro=cambio.centro_costo,
                obligacion=cambio.obligacion,
                estado=estado,
                evidencia=evidencia,
                fecha_fin=fecha_fin,
                version_obligacion=_version_en_fecha(
                    cambio.obligacion,
                    en_fecha=en_fecha,
                ),
            )
        )
    return casos
