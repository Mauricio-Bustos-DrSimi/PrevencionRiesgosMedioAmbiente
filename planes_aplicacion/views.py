from datetime import date
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from bitacora.registro import registrar_evento
from centros_costo.models import CentroCosto
from .forms import CambioAplicabilidadForm, MotivoAplicabilidadForm
from .models import CambioAplicabilidad
from .services import cambios_del_plan, estado_actual, obligaciones_sugeridas


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


def _centro(pk: int) -> CentroCosto:
    return get_object_or_404(CentroCosto, pk=pk, es_franquicia=False)


@requiere_prevencionista
def plan(request: HttpRequest, centro_pk: int) -> HttpResponse:
    centro = _centro(centro_pk)
    fecha_parametro = request.GET.get("fecha")
    fecha = date.fromisoformat(fecha_parametro) if fecha_parametro else None
    sugerencias = obligaciones_sugeridas(centro)
    cambios = cambios_del_plan(centro, hasta=fecha)
    items = [
        {
            "obligacion": obligacion,
            "cambio": estado_actual(centro, obligacion, hasta=fecha),
        }
        for obligacion in sugerencias
    ]
    return render(
        request,
        "planes_aplicacion/plan.html",
        {
            "centro": centro,
            "sugerencias": sugerencias,
            "items": items,
            "cambios": cambios,
            "fecha": fecha,
        },
    )


@requiere_prevencionista
def confirmar_sugerencia(request: HttpRequest, centro_pk: int) -> HttpResponse:
    centro = _centro(centro_pk)
    formulario = MotivoAplicabilidadForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            for obligacion in obligaciones_sugeridas(centro):
                if estado_actual(centro, obligacion) is None:
                    CambioAplicabilidad.objects.create(
                        centro_costo=centro,
                        obligacion=obligacion,
                        aplica=True,
                        motivo=formulario.cleaned_data["motivo"],
                        autor=actor,
                    )
            registrar_evento(
                actor=actor,
                accion="confirmar_sugerencia",
                entidad="plan de aplicación",
                identificador=str(centro.pk),
                descripcion=f"Confirmó la sugerencia para {centro.nombre}.",
                canal="web",
            )
        return redirect("planes_aplicacion:plan", centro_pk=centro.pk)
    return render(
        request,
        "planes_aplicacion/motivo.html",
        {
            "formulario": formulario,
            "titulo": "Confirmar plan sugerido",
            "centro": centro,
        },
    )


def _cambiar(request: HttpRequest, centro_pk: int, *, aplica: bool) -> HttpResponse:
    centro = _centro(centro_pk)
    formulario = CambioAplicabilidadForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        obligacion = formulario.cleaned_data["obligacion"]
        with transaction.atomic():
            CambioAplicabilidad.objects.create(
                centro_costo=centro,
                obligacion=obligacion,
                aplica=aplica,
                motivo=formulario.cleaned_data["motivo"],
                autor=actor,
            )
            registrar_evento(
                actor=actor,
                accion="aplicar" if aplica else "declarar_no_aplica",
                entidad="plan de aplicación",
                identificador=str(centro.pk),
                descripcion=f"Actualizó la aplicabilidad de {obligacion}.",
                canal="web",
            )
        return redirect("planes_aplicacion:plan", centro_pk=centro.pk)
    return render(
        request,
        "planes_aplicacion/motivo.html",
        {
            "formulario": formulario,
            "titulo": "Actualizar plan de aplicación",
            "centro": centro,
        },
    )


@requiere_prevencionista
def agregar(request: HttpRequest, centro_pk: int) -> HttpResponse:
    return _cambiar(request, centro_pk, aplica=True)


@requiere_prevencionista
def no_aplica(request: HttpRequest, centro_pk: int) -> HttpResponse:
    return _cambiar(request, centro_pk, aplica=False)
