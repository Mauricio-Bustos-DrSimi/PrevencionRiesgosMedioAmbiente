from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .permisos import es_operador_mvp

def inicio(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path())
    if not es_operador_mvp(request.user):
        raise PermissionDenied

    return render(request, "acceso/inicio.html")
