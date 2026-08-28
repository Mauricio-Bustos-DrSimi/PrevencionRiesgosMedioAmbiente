from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from acceso.permisos import requiere_operador_mvp
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import Obligacion
from planes_aplicacion.models import CambioAplicabilidad

from .models import EventoBitacora


@requiere_operador_mvp
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
    evidencias = Evidencia.objects.filter(
        centro_costo=centro,
        obligacion=obligacion,
    ).select_related("cargada_por", "validacion__validada_por", "version_obligacion")
    identificadores_evidencia = evidencias.values_list("pk", flat=True)
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
            | Q(
                centro_costo__isnull=True,
                obligacion__isnull=True,
                evidencia__isnull=True,
                entidad__iexact="plan de aplicación",
                identificador=str(centro.pk),
            )
        )
        .select_related("actor")
        .order_by("ocurrido_en", "pk")
    )
    cambios = CambioAplicabilidad.objects.filter(
        centro_costo=centro,
        obligacion=obligacion,
    ).select_related("autor")
    return render(
        request,
        "bitacora/recorrido.html",
        {
            "centro": centro,
            "obligacion": obligacion,
            "eventos": eventos,
            "cambios": cambios,
            "evidencias": evidencias,
        },
    )
