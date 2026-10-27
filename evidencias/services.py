import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from acceso.permisos import exigir_prevencionista
from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from configuracion.tiempo import fin_del_dia
from obligaciones.models import (
    ClasificacionEvidencia,
    Obligacion,
    Periodicidad,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad
from planes_aplicacion.services import estado_actual, estado_actual_trabajador
from trabajadores.models import Trabajador
from trabajadores.services import Dotacion, leer_dotacion

from .models import (
    CorreccionEvidencia,
    EstadoEvidencia,
    Evidencia,
    ValidacionEvidencia,
    exigir_titular_coherente,
)


class ErrorCargaEvidencia(Exception):
    """Indica que el archivo o el registro no pudo completarse."""


class RechazoCargaEvidencia(ErrorCargaEvidencia):
    """El dominio se niega a registrar esta evidencia: no es un fallo técnico.

    Se distingue del error de almacenamiento porque la respuesta es otra: aquí
    no hay nada que reintentar, la carga no correspondía.
    """


class ErrorValidacionEvidencia(Exception):
    """Indica que una evidencia no admite otra validación."""


class ErrorCorreccionEvidencia(Exception):
    """Indica que la corrección de fechas no se puede registrar."""


class EstadoCumplimiento(StrEnum):
    VIGENTE = "Vigente"
    POR_VENCER = "Por vencer"
    VENCIDO = "Vencido"
    PENDIENTE_VALIDACION = "Pendiente de validación"
    SIN_EVIDENCIA = "Sin evidencia"
    NO_APLICA = "No aplica"


# De peor a mejor. «Sin evidencia» y «Vencido» nunca se colapsan: no hacer algo
# nunca y dejarlo caer son faltas distintas. «Pendiente de validación» cuenta
# como no cumplido.
PRECEDENCIA_AGREGADO: tuple[EstadoCumplimiento, ...] = (
    EstadoCumplimiento.SIN_EVIDENCIA,
    EstadoCumplimiento.VENCIDO,
    EstadoCumplimiento.PENDIENTE_VALIDACION,
    EstadoCumplimiento.POR_VENCER,
    EstadoCumplimiento.VIGENTE,
)

ESTADOS_CON_VIGENCIA = {
    EstadoCumplimiento.VIGENTE,
    EstadoCumplimiento.POR_VENCER,
    EstadoCumplimiento.VENCIDO,
}


@dataclass(frozen=True)
class CasoCumplimiento:
    centro: CentroCosto
    obligacion: Obligacion
    estado: EstadoCumplimiento
    evidencia: Evidencia | None
    fecha_fin: date | None
    version_obligacion: VersionObligacion | None = None
    trabajador: Trabajador | None = None
    recuento: tuple[tuple[EstadoCumplimiento, int], ...] = ()
    trabajadores_aplicables: int = 0

    @property
    def nombre_obligacion(self) -> str:
        if self.version_obligacion is not None:
            return self.version_obligacion.nombre
        return str(self.obligacion)

    @property
    def es_agregado(self) -> bool:
        """El caso resume a varias personas en vez de acreditar a una."""
        return self.trabajador is None and self.trabajadores_aplicables > 0

    @property
    def cuantos_en_el_estado(self) -> int:
        for estado, cantidad in self.recuento:
            if estado == self.estado:
                return cantidad
        return 0


@dataclass(frozen=True)
class ResultadoIntegridad:
    hash_registrado: str
    hash_calculado: str | None
    coincide: bool
    error: str | None = None


@dataclass(frozen=True)
class FechasLeidas:
    """Lo que Prevención leyó en el papel, con el motivo que lo explica."""

    fecha_emision: date
    fecha_vencimiento: date
    motivo: str


@dataclass(frozen=True)
class FechasEfectivas:
    """Las fechas que rigen en una fecha dada, con o sin corrección."""

    fecha_emision: date
    fecha_vencimiento: date
    correccion: CorreccionEvidencia | None

    @property
    def fue_corregida(self) -> bool:
        return self.correccion is not None


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


def _es_salud_ocupacional(evidencia: Evidencia) -> bool:
    return (
        evidencia.version_obligacion.clasificacion_evidencia
        == ClasificacionEvidencia.SALUD_OCUPACIONAL
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
    trabajador: Trabajador | None = None,
    canal: str = "web",
) -> Evidencia:
    exigir_prevencionista(actor, "cargar evidencia")
    version = obligacion.version_actual
    # El titular se hace valer antes que la aplicabilidad: si la evidencia se
    # está atribuyendo al titular equivocado, el motivo del rechazo tiene que
    # decir eso y no un «No aplica» que no explica nada.
    try:
        exigir_titular_coherente(
            version=version,
            centro=centro,
            trabajador=trabajador,
        )
    except ValidationError as exc:
        raise RechazoCargaEvidencia("; ".join(exc.messages)) from exc

    # Tras la comprobación anterior, que haya trabajador equivale a que la
    # obligación sea suya, y el plan que manda es el de su titular.
    cambio = (
        estado_actual_trabajador(trabajador, obligacion)
        if trabajador is not None
        else estado_actual(centro, obligacion)
    )
    if cambio is None or not cambio.aplica:
        raise RechazoCargaEvidencia("No aplica: no se puede cargar esta evidencia.")

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
                version_obligacion=version,
                trabajador=trabajador,
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
                descripcion=(
                    "Cargó una evidencia de salud ocupacional para un titular "
                    "autorizado."
                    if _es_salud_ocupacional(evidencia)
                    else (
                        f"Cargó evidencia para {obligacion}"
                        + (
                            f" a nombre de {trabajador.nombre} ({trabajador.rut})."
                            if trabajador is not None
                            else "."
                        )
                    )
                ),
                canal=canal,
                contexto=ContextoBitacora.para_evidencia(evidencia),
            )
    except ValidationError as exc:
        if evidencia is not None and evidencia.archivo.name:
            evidencia.archivo.storage.delete(evidencia.archivo.name)
        raise RechazoCargaEvidencia("; ".join(exc.messages)) from exc
    except Exception as exc:
        if evidencia is not None and evidencia.archivo.name:
            evidencia.archivo.storage.delete(evidencia.archivo.name)
        raise ErrorCargaEvidencia(
            "No se pudo almacenar la evidencia; no se registró ninguna evidencia parcial."
        ) from exc
    return evidencia


def _comprobar_fechas(fecha_emision: date, fecha_vencimiento: date) -> None:
    if fecha_emision > timezone.localdate():
        raise ErrorCorreccionEvidencia("La fecha de emisión no puede ser futura.")
    if fecha_vencimiento <= fecha_emision:
        raise ErrorCorreccionEvidencia(
            "La fecha de vencimiento debe ser posterior a la emisión."
        )


def corregir_evidencia(
    *,
    evidencia: Evidencia,
    actor: User,
    fecha_emision: date,
    fecha_vencimiento: date,
    motivo: str,
    canal: str = "web",
) -> CorreccionEvidencia:
    """Deja escrito lo que Prevención leyó en el documento.

    La evidencia no se toca. Corregir una fecha no es cargar una evidencia
    nueva: no llegó otro documento, se leyó bien el que ya estaba.
    """
    exigir_prevencionista(actor, "corregir las fechas de una evidencia")
    _comprobar_fechas(fecha_emision, fecha_vencimiento)

    with transaction.atomic():
        correccion = CorreccionEvidencia.objects.create(
            evidencia=evidencia,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            motivo=motivo,
            autor=actor,
        )
        registrar_evento(
            actor=actor,
            accion="corregir_fechas_evidencia",
            entidad="Evidencia",
            identificador=str(evidencia.pk),
            descripcion=(
                "Corrigió las fechas de una evidencia de salud ocupacional. "
                "El archivo y su hash no cambian."
                if _es_salud_ocupacional(evidencia)
                else (
                    f"Corrigió las fechas leídas del documento de "
                    f"{evidencia.nombre_obligacion}: emisión "
                    f"{fecha_emision.isoformat()} y vencimiento "
                    f"{fecha_vencimiento.isoformat()}. El archivo y su hash no "
                    "cambian."
                )
            ),
            canal=canal,
            contexto=ContextoBitacora.para_evidencia(evidencia),
        )
    return correccion


def validar_evidencia(
    *,
    evidencia: Evidencia,
    actor: User,
    canal: str = "web",
    correccion: FechasLeidas | None = None,
) -> ValidacionEvidencia:
    """Confirma la evidencia, corrigiendo antes sus fechas si hace falta.

    Corregir y validar son actos distintos —uno enmienda lo que el sistema
    leyó, el otro confirma el documento— y quedan por separado en la bitácora
    aunque el Prevencionista los resuelva en un solo envío.
    """
    exigir_prevencionista(actor, "validar evidencia")
    if evidencia.estado_validacion == EstadoEvidencia.VALIDADA:
        raise ErrorValidacionEvidencia("La evidencia ya fue validada.")
    if correccion is not None:
        _comprobar_fechas(correccion.fecha_emision, correccion.fecha_vencimiento)

    with transaction.atomic():
        if correccion is not None:
            corregir_evidencia(
                evidencia=evidencia,
                actor=actor,
                fecha_emision=correccion.fecha_emision,
                fecha_vencimiento=correccion.fecha_vencimiento,
                motivo=correccion.motivo,
                canal=canal,
            )
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
                "Validó una evidencia de salud ocupacional; confirmó su "
                "correspondencia y sus fechas."
                if _es_salud_ocupacional(evidencia)
                else (
                    f"Validó evidencia para {evidencia.nombre_obligacion} "
                    f"(versión {evidencia.version_obligacion.numero}); confirmó "
                    "su correspondencia y sus fechas."
                )
            ),
            canal=canal,
            contexto=ContextoBitacora.para_evidencia(evidencia),
        )
    return validacion


def _sumar_anos(fecha: date, anos: int) -> date:
    try:
        return fecha.replace(year=fecha.year + anos)
    except ValueError:
        return fecha.replace(year=fecha.year + anos, month=2, day=28)


def fin_de_vigencia(
    *,
    fecha_emision: date,
    fecha_vencimiento: date,
    periodicidad: Periodicidad,
) -> date:
    """Hasta cuándo sirve una evidencia con estas fechas y esta periodicidad.

    La fecha que trae el documento no manda por sí sola: si la obligación se
    renueva más seguido que lo que el emisor concede, manda el ciclo. Por eso
    se toma el menor de los dos.
    """
    if periodicidad == Periodicidad.PERMANENTE:
        return date.max
    if periodicidad == Periodicidad.ANUAL:
        return min(fecha_vencimiento, _sumar_anos(fecha_emision, 1))
    if periodicidad == Periodicidad.BIENAL:
        return min(fecha_vencimiento, _sumar_anos(fecha_emision, 2))
    return fecha_vencimiento


def fechas_efectivas(
    evidencia: Evidencia,
    *,
    en_fecha: date | None = None,
) -> FechasEfectivas:
    """Las fechas que rigen: las del documento, o la corrección más reciente.

    Manda la corrección más reciente anterior a la fecha consultada, de modo
    que reconstruir el pasado siga usando el dato que regía entonces.
    """
    correcciones = [
        correccion
        for correccion in evidencia.correcciones.all()
        if en_fecha is None
        or timezone.localdate(correccion.ocurrido_en) <= en_fecha
    ]
    if not correcciones:
        return FechasEfectivas(
            fecha_emision=evidencia.fecha_emision,
            fecha_vencimiento=evidencia.fecha_vencimiento,
            correccion=None,
        )
    vigente = max(correcciones, key=lambda c: (c.ocurrido_en, c.pk))
    return FechasEfectivas(
        fecha_emision=vigente.fecha_emision,
        fecha_vencimiento=vigente.fecha_vencimiento,
        correccion=vigente,
    )


def fecha_fin_vigencia(
    evidencia: Evidencia,
    *,
    en_fecha: date | None = None,
) -> date:
    fechas = fechas_efectivas(evidencia, en_fecha=en_fecha)
    return fin_de_vigencia(
        fecha_emision=fechas.fecha_emision,
        fecha_vencimiento=fechas.fecha_vencimiento,
        periodicidad=evidencia.periodicidad,
    )


def evidencia_esta_vigente(evidencia: Evidencia, *, en_fecha: date) -> bool:
    fechas = fechas_efectivas(evidencia, en_fecha=en_fecha)
    return (
        fechas.fecha_emision
        <= en_fecha
        <= fecha_fin_vigencia(evidencia, en_fecha=en_fecha)
    )


def estado_de_evidencia_validada(
    evidencia: Evidencia,
    *,
    en_fecha: date,
) -> EstadoCumplimiento:
    fechas = fechas_efectivas(evidencia, en_fecha=en_fecha)
    fin = fecha_fin_vigencia(evidencia, en_fecha=en_fecha)
    if en_fecha < fechas.fecha_emision:
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


def _version_en_fecha(
    obligacion: Obligacion,
    *,
    en_fecha: date,
) -> VersionObligacion | None:
    # Se filtra en memoria para que `prefetch_related("versiones")` evite una
    # consulta por obligación al recorrer un catálogo entero.
    limite = fin_del_dia(en_fecha)
    vigentes = [
        version
        for version in obligacion.versiones.all()
        if version.creada_en <= limite
    ]
    return max(vigentes, key=lambda version: version.numero, default=None)


def _evidencia_relevante(
    evidencias: list[Evidencia],
    *,
    en_fecha: date,
) -> Evidencia | None:
    for evidencia in evidencias:
        if fechas_efectivas(evidencia, en_fecha=en_fecha).fecha_emision <= en_fecha:
            return evidencia
    return min(
        evidencias,
        key=lambda evidencia: (
            fechas_efectivas(evidencia, en_fecha=en_fecha).fecha_emision,
            evidencia.cargada_en,
            evidencia.pk,
        ),
        default=None,
    )


def _evidencias_de(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    en_fecha: date,
    trabajador: Trabajador | None,
) -> list[Evidencia]:
    consulta = Evidencia.objects.filter(
        centro_costo=centro,
        obligacion=obligacion,
        cargada_en__lte=fin_del_dia(en_fecha),
    )
    if trabajador is not None:
        consulta = consulta.filter(trabajador=trabajador)
    else:
        consulta = consulta.filter(trabajador__isnull=True)
    return list(
        consulta.select_related("version_obligacion", "validacion").prefetch_related(
            "correcciones"
        )
    )


def _estado_desde_evidencias(
    evidencias: list[Evidencia],
    *,
    en_fecha: date,
) -> tuple[EstadoCumplimiento, Evidencia | None, date | None]:
    evidencia = _evidencia_relevante(evidencias, en_fecha=en_fecha)
    if evidencia is None:
        return EstadoCumplimiento.SIN_EVIDENCIA, None, None
    estado = estado_de_evidencia(evidencia, en_fecha=en_fecha)
    fecha_fin = (
        fecha_fin_vigencia(evidencia, en_fecha=en_fecha)
        if estado in ESTADOS_CON_VIGENCIA
        else None
    )
    return estado, evidencia, fecha_fin


def _titular_en_fecha(
    obligacion: Obligacion,
    *,
    en_fecha: date,
) -> tuple[TitularObligacion, VersionObligacion | None]:
    version = _version_en_fecha(obligacion, en_fecha=en_fecha)
    if version is None:
        return TitularObligacion.CENTRO_COSTO, None
    return TitularObligacion(version.titular), version


def _caso_de_una_persona(
    *,
    trabajador: Trabajador,
    obligacion: Obligacion,
    centro: CentroCosto,
    version: VersionObligacion | None,
    cambio: CambioAplicabilidad,
    evidencias: list[Evidencia],
    en_fecha: date,
    validado: bool,
) -> CasoCumplimiento:
    """Arma el caso de una persona con lo que ya se leyó de la base.

    No consulta nada: recibe su plan y sus evidencias resueltos, porque a la
    escala del piloto esto se ejecuta miles de veces por pantalla.
    """
    if not cambio.aplica:
        return CasoCumplimiento(
            centro=centro,
            obligacion=obligacion,
            estado=EstadoCumplimiento.NO_APLICA,
            evidencia=None,
            fecha_fin=None,
            version_obligacion=version,
            trabajador=trabajador,
        )
    estado, evidencia, fecha_fin = _estado_desde_evidencias(
        evidencias,
        en_fecha=en_fecha,
    )
    if not validado and estado != EstadoCumplimiento.SIN_EVIDENCIA:
        # Un trabajador que Prevención todavía no incorporó no acredita nada:
        # su documento existe, pero la cobertura del centro no crece porque
        # alguien haya creado una ficha.
        estado = EstadoCumplimiento.PENDIENTE_VALIDACION
        fecha_fin = None
    return CasoCumplimiento(
        centro=centro,
        obligacion=obligacion,
        estado=estado,
        evidencia=evidencia,
        fecha_fin=fecha_fin,
        version_obligacion=version,
        trabajador=trabajador,
    )


def caso_de_trabajador(
    *,
    trabajador: Trabajador,
    obligacion: Obligacion,
    en_fecha: date,
    centro: CentroCosto | None = None,
    dotacion: Dotacion | None = None,
) -> CasoCumplimiento | None:
    """El estado de cumplimiento de una persona para una obligación suya."""
    cambio = estado_actual_trabajador(trabajador, obligacion, hasta=en_fecha)
    if cambio is None:
        return None
    dotacion = dotacion or leer_dotacion(en_fecha=en_fecha)
    contexto = centro or dotacion.centro_de(trabajador)
    if contexto is None:
        return None
    _, version = _titular_en_fecha(obligacion, en_fecha=en_fecha)
    return _caso_de_una_persona(
        trabajador=trabajador,
        obligacion=obligacion,
        centro=contexto,
        version=version,
        cambio=cambio,
        evidencias=_evidencias_de(
            centro=contexto,
            obligacion=obligacion,
            en_fecha=en_fecha,
            trabajador=trabajador,
        ),
        en_fecha=en_fecha,
        validado=dotacion.esta_validado(trabajador),
    )


def _ultimo_por_trabajador(
    cambios: list[CambioAplicabilidad],
) -> dict[int, CambioAplicabilidad]:
    ultimos: dict[int, CambioAplicabilidad] = {}
    for cambio in cambios:
        if cambio.trabajador_id is not None:
            ultimos.setdefault(cambio.trabajador_id, cambio)
    return ultimos


def _evidencias_por_trabajador(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    personas: list[Trabajador],
    en_fecha: date,
) -> dict[int, list[Evidencia]]:
    agrupadas: defaultdict[int, list[Evidencia]] = defaultdict(list)
    consulta = (
        Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
            trabajador__in=personas,
            cargada_en__lte=fin_del_dia(en_fecha),
        )
        .select_related("version_obligacion", "validacion")
        .prefetch_related("correcciones")
    )
    for evidencia in consulta:
        if evidencia.trabajador_id is not None:
            agrupadas[evidencia.trabajador_id].append(evidencia)
    return agrupadas


def casos_de_la_dotacion(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    en_fecha: date,
    dotacion: Dotacion | None = None,
) -> list[CasoCumplimiento]:
    """El desglose por persona de una obligación de titular trabajador.

    Lee el plan y las evidencias de toda la dotación de una vez: preguntarlo
    persona por persona son miles de consultas para pintar una pantalla.
    """
    dotacion = dotacion or leer_dotacion(en_fecha=en_fecha)
    personas = dotacion.del_centro(centro)
    if not personas:
        return []
    _, version = _titular_en_fecha(obligacion, en_fecha=en_fecha)
    planes = _ultimo_por_trabajador(
        list(
            CambioAplicabilidad.objects.filter(
                trabajador__in=personas,
                obligacion=obligacion,
                ocurrido_en__lte=fin_del_dia(en_fecha),
            ).order_by("trabajador_id", "-ocurrido_en", "-pk")
        )
    )
    evidencias = _evidencias_por_trabajador(
        centro=centro,
        obligacion=obligacion,
        personas=[persona for persona in personas if persona.pk in planes],
        en_fecha=en_fecha,
    )
    return [
        _caso_de_una_persona(
            trabajador=persona,
            obligacion=obligacion,
            centro=centro,
            version=version,
            cambio=planes[persona.pk],
            evidencias=evidencias.get(persona.pk, []),
            en_fecha=en_fecha,
            validado=True,
        )
        for persona in personas
        if persona.pk in planes
    ]


def _agregar(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    version: VersionObligacion | None,
    casos: list[CasoCumplimiento],
) -> CasoCumplimiento:
    """El peor estado presente, con cuántas personas hay en cada uno.

    El promedio escondería a la única persona sin cobertura, que es
    justamente a quien hay que citar.
    """
    aplicables = [caso for caso in casos if caso.estado != EstadoCumplimiento.NO_APLICA]
    if not aplicables:
        return CasoCumplimiento(
            centro=centro,
            obligacion=obligacion,
            estado=EstadoCumplimiento.NO_APLICA,
            evidencia=None,
            fecha_fin=None,
            version_obligacion=version,
        )
    conteo = Counter(caso.estado for caso in aplicables)
    recuento = tuple(
        (estado, conteo[estado]) for estado in PRECEDENCIA_AGREGADO if conteo[estado]
    )
    peor = next(estado for estado in PRECEDENCIA_AGREGADO if conteo[estado])
    return CasoCumplimiento(
        centro=centro,
        obligacion=obligacion,
        estado=peor,
        evidencia=None,
        fecha_fin=None,
        version_obligacion=version,
        recuento=recuento,
        trabajadores_aplicables=len(aplicables),
    )


def caso_de_cumplimiento(
    *,
    centro: CentroCosto,
    obligacion: Obligacion,
    en_fecha: date,
    dotacion: Dotacion | None = None,
) -> CasoCumplimiento | None:
    titular, version = _titular_en_fecha(obligacion, en_fecha=en_fecha)
    if titular == TitularObligacion.TRABAJADOR:
        # Sin nadie a quien le aplique, la obligación no se le puede exigir al
        # centro: es No aplica con fundamento, no una fila en blanco.
        return _agregar(
            centro=centro,
            obligacion=obligacion,
            version=version,
            casos=casos_de_la_dotacion(
                centro=centro,
                obligacion=obligacion,
                en_fecha=en_fecha,
                dotacion=dotacion,
            ),
        )

    cambio = estado_actual(centro, obligacion, hasta=en_fecha)
    if cambio is None:
        return None
    if not cambio.aplica:
        return CasoCumplimiento(
            centro=centro,
            obligacion=obligacion,
            estado=EstadoCumplimiento.NO_APLICA,
            evidencia=None,
            fecha_fin=None,
            version_obligacion=version,
        )
    estado, evidencia, fecha_fin = _estado_desde_evidencias(
        _evidencias_de(
            centro=centro,
            obligacion=obligacion,
            en_fecha=en_fecha,
            trabajador=None,
        ),
        en_fecha=en_fecha,
    )
    return CasoCumplimiento(
        centro=centro,
        obligacion=obligacion,
        estado=estado,
        evidencia=evidencia,
        fecha_fin=fecha_fin,
        version_obligacion=version,
    )


def _ultimos_cambios(
    cambios: list[CambioAplicabilidad],
) -> list[CambioAplicabilidad]:
    ultimos: dict[tuple[int | None, int | None, int], CambioAplicabilidad] = {}
    for cambio in cambios:
        clave = (cambio.centro_costo_id, cambio.trabajador_id, cambio.obligacion_id)
        ultimos.setdefault(clave, cambio)
    return list(ultimos.values())


def casos_de_cumplimiento(*, en_fecha: date) -> list[CasoCumplimiento]:
    """Todos los casos operables, en el grano de su titular.

    Las obligaciones de titular trabajador se enumeran persona por persona: una
    bandeja que muestre el agregado no dice a quién hay que citar.
    """
    casos: list[CasoCumplimiento] = []

    cambios_centro = _ultimos_cambios(
        list(
            CambioAplicabilidad.objects.filter(
                centro_costo__es_franquicia=False,
            )
            .select_related("centro_costo", "obligacion")
            .prefetch_related("obligacion__versiones")
            .order_by("centro_costo_id", "obligacion_id", "-ocurrido_en", "-pk")
        )
    )
    for cambio in cambios_centro:
        obligacion = cambio.obligacion
        centro = cambio.centro_costo
        if centro is None or not obligacion.esta_vigente:
            continue
        titular, version = _titular_en_fecha(obligacion, en_fecha=en_fecha)
        if titular != TitularObligacion.CENTRO_COSTO:
            # La obligación pasó a tener otro titular: el centro ya no responde
            # por ella y su desglose se enumera por persona más abajo.
            continue
        if not cambio.aplica:
            casos.append(
                CasoCumplimiento(
                    centro=centro,
                    obligacion=obligacion,
                    estado=EstadoCumplimiento.NO_APLICA,
                    evidencia=None,
                    fecha_fin=None,
                    version_obligacion=version,
                )
            )
            continue
        estado, evidencia, fecha_fin = _estado_desde_evidencias(
            _evidencias_de(
                centro=centro,
                obligacion=obligacion,
                en_fecha=en_fecha,
                trabajador=None,
            ),
            en_fecha=en_fecha,
        )
        casos.append(
            CasoCumplimiento(
                centro=centro,
                obligacion=obligacion,
                estado=estado,
                evidencia=evidencia,
                fecha_fin=fecha_fin,
                version_obligacion=version,
            )
        )

    casos.extend(_casos_por_persona(en_fecha=en_fecha))
    return casos


def _casos_por_persona(*, en_fecha: date) -> list[CasoCumplimiento]:
    """Enumera, persona por persona, lo que su plan individual le exige.

    Resuelve la dotación, los planes y las evidencias en tres consultas y
    arma el resto en memoria: a la escala del piloto —129 trabajadores por 14
    obligaciones— preguntarlo caso por caso son miles de consultas.
    """
    dotacion = leer_dotacion(en_fecha=en_fecha)
    cambios = _ultimos_cambios(
        list(
            CambioAplicabilidad.objects.filter(trabajador__isnull=False)
            .select_related("trabajador", "obligacion")
            .prefetch_related("obligacion__versiones")
            .order_by("trabajador_id", "obligacion_id", "-ocurrido_en", "-pk")
        )
    )

    pertinentes: list[tuple[CambioAplicabilidad, Trabajador, CentroCosto]] = []
    for cambio in cambios:
        trabajador = dotacion.personas.get(cambio.trabajador_id or 0)
        if trabajador is None or not dotacion.produce_cumplimiento(trabajador):
            continue
        contexto = dotacion.centro_de(trabajador)
        if contexto is None or contexto.es_franquicia:
            continue
        if not cambio.obligacion.esta_vigente:
            continue
        pertinentes.append((cambio, trabajador, contexto))

    evidencias = _evidencias_por_persona_y_obligacion(
        pares={
            (trabajador.pk, cambio.obligacion_id)
            for cambio, trabajador, _ in pertinentes
        },
        en_fecha=en_fecha,
    )
    versiones: dict[int, VersionObligacion | None] = {}
    casos: list[CasoCumplimiento] = []
    for cambio, trabajador, contexto in pertinentes:
        obligacion = cambio.obligacion
        if obligacion.pk not in versiones:
            versiones[obligacion.pk] = _version_en_fecha(obligacion, en_fecha=en_fecha)
        casos.append(
            _caso_de_una_persona(
                trabajador=trabajador,
                obligacion=obligacion,
                centro=contexto,
                version=versiones[obligacion.pk],
                cambio=cambio,
                evidencias=evidencias.get((trabajador.pk, obligacion.pk), []),
                en_fecha=en_fecha,
                validado=True,
            )
        )
    return casos


def _evidencias_por_persona_y_obligacion(
    *,
    pares: set[tuple[int, int]],
    en_fecha: date,
) -> dict[tuple[int, int], list[Evidencia]]:
    agrupadas: defaultdict[tuple[int, int], list[Evidencia]] = defaultdict(list)
    if not pares:
        return agrupadas
    consulta = (
        Evidencia.objects.filter(
            trabajador_id__in={trabajador for trabajador, _ in pares},
            obligacion_id__in={obligacion for _, obligacion in pares},
            cargada_en__lte=fin_del_dia(en_fecha),
        )
        .select_related("version_obligacion", "validacion")
        .prefetch_related("correcciones")
    )
    for evidencia in consulta:
        clave = (evidencia.trabajador_id or 0, evidencia.obligacion_id)
        if clave in pares:
            agrupadas[clave].append(evidencia)
    return agrupadas
