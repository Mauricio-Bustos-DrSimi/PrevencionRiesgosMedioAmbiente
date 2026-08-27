from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


GRUPO_PREVENCIONISTA = "Prevencionista"


@login_required
def inicio(request: HttpRequest) -> HttpResponse:
    usuario = request.user
    if not (
        usuario.is_superuser
        or usuario.groups.filter(name=GRUPO_PREVENCIONISTA).exists()
    ):
        raise PermissionDenied

    return render(request, "acceso/inicio.html")
