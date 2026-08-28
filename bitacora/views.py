from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import Obligacion
from planes_aplicacion.models import CambioAplicabilidad

from .models import EventoBitacora


Parametros = ParamSpec("Parametros")
Respuesta = TypeVar("Respuesta", bound=HttpResponse)


def requiere_fiscalizador(
    vista: Callable[Parametros, Respuesta],
) -> Callable[Parametros, Respuesta]:
    @login_required
    @wraps(vista)
    def protegida(
        *args: Parametros.args,
        **kwargs: Parametros.kwargs,
    ) -> Respuesta:
        request = cast(HttpRequest, args[0])
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name="Prevencionista").exists()
        ):
            raise PermissionDenied
        return vista(*args, **kwargs)

    return protegida


@requiere_fiscalizador
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
    eventos = (
        EventoBitacora.objects.filter(
            Q(centro_costo=centro, obligacion=obligacion)
            | Q(centro_costo=centro, obligacion__isnull=True)
            | Q(centro_costo__isnull=True, obligacion=obligacion)
        )
        .select_related("actor")
        .order_by("ocurrido_en", "pk")
    )
    cambios = CambioAplicabilidad.objects.filter(
        centro_costo=centro,
        obligacion=obligacion,
    ).select_related("autor")
    evidencias = Evidencia.objects.filter(
        centro_costo=centro,
        obligacion=obligacion,
    ).select_related("cargada_por", "validacion__validada_por", "version_obligacion")
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
