from collections.abc import Callable
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import CentroCosto


GRUPO_PREVENCIONISTA = "Prevencionista"


def requiere_acceso_centros(
    vista: Callable[[HttpRequest, int | None], HttpResponse],
) -> Callable[[HttpRequest, int | None], HttpResponse]:
    @wraps(vista)
    def vista_protegida(
        request: HttpRequest,
        pk: int | None = None,
    ) -> HttpResponse:
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        if not (
            request.user.is_superuser
            or request.user.groups.filter(name=GRUPO_PREVENCIONISTA).exists()
        ):
            raise PermissionDenied
        return vista(request, pk)

    return vista_protegida


@requiere_acceso_centros
def lista_centros_costo(
    request: HttpRequest,
    pk: int | None = None,
) -> HttpResponse:
    del pk
    centros = CentroCosto.objects.filter(es_franquicia=False)
    return render(
        request,
        "centros_costo/lista.html",
        {"centros_costo": centros},
    )

@requiere_acceso_centros
def detalle_centro_costo(
    request: HttpRequest,
    pk: int | None = None,
) -> HttpResponse:
    centro = get_object_or_404(
        CentroCosto,
        pk=pk,
        es_franquicia=False,
    )
    return render(
        request,
        "centros_costo/detalle.html",
        {"centro_costo": centro},
    )
