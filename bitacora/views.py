from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from acceso.permisos import (
    exigir_acceso_evidencia,
    exigir_acceso_version_evidencia,
    requiere_modificador_mvp,
)
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import ClasificacionEvidencia, Obligacion
from planes_aplicacion.models import CambioAplicabilidad

from .models import EventoBitacora


@requiere_modificador_mvp
def recorrido(
    request: HttpRequest,
    centro_pk: int,
    obligacion_pk: int,
) -> HttpResponse:
    centro = get_object_or_404(CentroCosto, pk=centro_pk, es_franquicia=False)
    obligacion = get_object_or_404(
        Obligacion.objects.prefetch_related("versiones__autor"),
        pk=obligacion_pk,
    )
    for version in obligacion.versiones.all():
        exigir_acceso_version_evidencia(request.user, version)
    evidencias = list(
        Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
        )
        .select_related(
            "cargada_por",
            "validacion__validada_por",
            "version_obligacion",
            "trabajador",
        )
        .prefetch_related("correcciones__autor")
    )
    for evidencia in evidencias:
        exigir_acceso_evidencia(request.user, evidencia)
    es_salud_ocupacional = any(
        version.clasificacion_evidencia
        == ClasificacionEvidencia.SALUD_OCUPACIONAL
        for version in obligacion.versiones.all()
    )
    # La bitácora guarda el identificador como texto (`str(evidencia.pk)`), así que
    # la búsqueda debe comparar texto contra texto: PostgreSQL no compara varchar
    # con bigint.
    identificadores_evidencia = [str(evidencia.pk) for evidencia in evidencias]
    eventos = (
        EventoBitacora.objects.filter(
            Q(centro_costo=centro, obligacion=obligacion)
            | Q(centro_costo=centro, obligacion__isnull=True)
            | Q(centro_costo__isnull=True, obligacion=obligacion)
            | Q(
                centro_costo__isnull=True,
                obligacion__isnull=True,
                evidencia__isnull=True,
                entidad__iexact="Centro de costo",
                identificador=centro.codigo_contable,
            )
            | Q(
                centro_costo__isnull=True,
                obligacion__isnull=True,
                evidencia__isnull=True,
                entidad__iexact="Obligación",
                identificador=str(obligacion.pk),
            )
            | Q(
                centro_costo__isnull=True,
                obligacion__isnull=True,
                evidencia__isnull=True,
                entidad__iexact="Evidencia",
                identificador__in=identificadores_evidencia,
            )
        )
        .select_related("actor")
        .order_by("ocurrido_en", "pk")
    )
    # El plan de una obligación de titular trabajador no cuelga del centro,
    # pero se decide para la gente del centro: la trazabilidad de la
    # instalación tiene que mostrarlo igual, con su autor y su motivo.
    cambios = (
        CambioAplicabilidad.objects.filter(
            Q(centro_costo=centro)
            | Q(trabajador__asignaciones__centro_costo=centro),
            obligacion=obligacion,
        )
        .select_related("autor", "trabajador")
        .distinct()
    )
    return render(
        request,
        "bitacora/recorrido.html",
        {
            "centro": centro,
            "obligacion": obligacion,
            "eventos": eventos,
            "cambios": cambios,
            "evidencias": evidencias,
            "es_salud_ocupacional": es_salud_ocupacional,
        },
    )
