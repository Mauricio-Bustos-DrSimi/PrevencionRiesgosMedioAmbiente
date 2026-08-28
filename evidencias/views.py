from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion
from planes_aplicacion.services import estado_actual

from .forms import EvidenciaForm
from .models import Evidencia
from .services import (
    ErrorCargaEvidencia,
    ErrorValidacionEvidencia,
    cargar_evidencia,
    evidencia_esta_vigente,
    validar_evidencia,
)

Parametros = ParamSpec("Parametros")
Respuesta = TypeVar("Respuesta", bound=HttpResponse)


def requiere_prevencionista(
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


@requiere_prevencionista
def cargar(request: HttpRequest, centro_pk: int, obligacion_pk: int) -> HttpResponse:
    centro = get_object_or_404(CentroCosto, pk=centro_pk, es_franquicia=False)
    obligacion = get_object_or_404(Obligacion, pk=obligacion_pk)
    formulario = EvidenciaForm(request.POST or None, request.FILES or None)
    error = None
    cambio = estado_actual(centro, obligacion)
    if cambio is None or not cambio.aplica:
        error = "No aplica: no se puede cargar esta evidencia."
        return render(
            request,
            "evidencias/formulario.html",
            {"formulario": formulario, "centro": centro, "obligacion": obligacion, "error": error},
            status=403,
        )
    if request.method == "POST" and formulario.is_valid():
        try:
            evidencia = cargar_evidencia(
                centro=centro,
                obligacion=obligacion,
                actor=cast(User, request.user),
                archivo=formulario.cleaned_data["archivo"],
                emisor=formulario.cleaned_data["emisor"],
                fecha_emision=formulario.cleaned_data["fecha_emision"],
                fecha_vencimiento=formulario.cleaned_data["fecha_vencimiento"],
            )
        except ErrorCargaEvidencia as exc:
            error = str(exc)
        else:
            return render(
                request,
                "evidencias/cargada.html",
                {"centro": centro, "obligacion": obligacion, "evidencia": evidencia},
            )
    return render(
        request,
        "evidencias/formulario.html",
        {"formulario": formulario, "centro": centro, "obligacion": obligacion, "error": error},
    )


@requiere_prevencionista
def pendientes(request: HttpRequest) -> HttpResponse:
    evidencias = Evidencia.objects.filter(
        validacion__isnull=True,
    ).select_related("centro_costo", "obligacion")
    return render(
        request,
        "evidencias/pendientes.html",
        {"evidencias": evidencias},
    )


@requiere_prevencionista
def validar(request: HttpRequest, evidencia_pk: int) -> HttpResponse:
    evidencia = get_object_or_404(
        Evidencia.objects.select_related("centro_costo", "obligacion"),
        pk=evidencia_pk,
    )
    error = None
    if request.method == "POST":
        try:
            validar_evidencia(
                evidencia=evidencia,
                actor=cast(User, request.user),
            )
        except ErrorValidacionEvidencia as exc:
            error = str(exc)
        else:
            return redirect("evidencias:validar", evidencia_pk=evidencia.pk)

    validacion = getattr(evidencia, "validacion", None)
    vigente = validacion is not None and evidencia_esta_vigente(
        evidencia,
        en_fecha=timezone.localdate(),
    )
    return render(
        request,
        "evidencias/validar.html",
        {
            "evidencia": evidencia,
            "validacion": validacion,
            "vigente": vigente,
            "error": error,
        },
    )
