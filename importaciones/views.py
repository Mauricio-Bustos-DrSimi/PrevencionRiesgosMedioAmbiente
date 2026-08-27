from io import TextIOWrapper

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .forms import ImportacionForm
from .services import importar_centros, importar_obligaciones


@login_required
def importar(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        raise PermissionDenied
    formulario = ImportacionForm(request.POST or None, request.FILES or None)
    resultado = None
    if request.method == "POST" and formulario.is_valid():
        archivo = TextIOWrapper(
            formulario.cleaned_data["archivo"].file,
            encoding="utf-8-sig",
        )
        tipo = formulario.cleaned_data["tipo"]
        actor = request.user
        if tipo == ImportacionForm.TIPO_CENTROS:
            resultado = importar_centros(archivo, actor)
        else:
            resultado = importar_obligaciones(archivo, actor)
    return render(
        request,
        "importaciones/importar.html",
        {"formulario": formulario, "resultado": resultado},
    )
