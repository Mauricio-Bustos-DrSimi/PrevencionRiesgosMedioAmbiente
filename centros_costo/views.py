from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from acceso.permisos import (
    centros_visibles_para,
    exigir_acceso_centro,
    requiere_operador_mvp,
)

from .models import CentroCosto


@requiere_operador_mvp
def lista_centros_costo(
    request: HttpRequest,
    pk: int | None = None,
) -> HttpResponse:
    del pk
    centros = centros_visibles_para(request.user)
    return render(
        request,
        "centros_costo/lista.html",
        {"centros_costo": centros},
    )

@requiere_operador_mvp
def detalle_centro_costo(
    request: HttpRequest,
    pk: int | None = None,
) -> HttpResponse:
    centro = get_object_or_404(
        CentroCosto,
        pk=pk,
        es_franquicia=False,
    )
    exigir_acceso_centro(request.user, centro)
    return render(
        request,
        "centros_costo/detalle.html",
        {"centro_costo": centro},
    )
