from io import TextIOWrapper
from typing import cast

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from acceso.permisos import requiere_modificador_mvp

from .forms import ImportacionForm
from .services import importar_centros, importar_obligaciones


@requiere_modificador_mvp
def importar(request: HttpRequest) -> HttpResponse:
    formulario = ImportacionForm(request.POST or None, request.FILES or None)
    resultado = None
    if request.method == "POST" and formulario.is_valid():
        archivo = TextIOWrapper(
            formulario.cleaned_data["archivo"].file,
            encoding="utf-8-sig",
        )
        tipo = formulario.cleaned_data["tipo"]
        actor = cast(User, request.user)
        if tipo == ImportacionForm.TIPO_CENTROS:
            resultado = importar_centros(archivo, actor)
        else:
            resultado = importar_obligaciones(archivo, actor)
    return render(
        request,
        "importaciones/importar.html",
        {"formulario": formulario, "resultado": resultado},
    )
from acceso.permisos import requiere_modificador_mvp
