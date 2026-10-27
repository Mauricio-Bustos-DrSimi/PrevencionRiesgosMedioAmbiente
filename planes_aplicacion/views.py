from datetime import date
from typing import cast

from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from acceso.permisos import (
    exigir_acceso_centro,
    exigir_acceso_version_evidencia,
    puede_acceder_version_evidencia,
    requiere_modificador_mvp,
    requiere_operador_mvp,
)
from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from evidencias.services import caso_de_cumplimiento, casos_de_la_dotacion
from obligaciones.models import Obligacion
from trabajadores.services import leer_dotacion
from .forms import CambioAplicabilidadForm, MotivoAplicabilidadForm
from .models import CambioAplicabilidad
from .services import (
    cambios_del_plan,
    estado_actual,
    obligaciones_de_la_dotacion,
    obligaciones_sugeridas,
)


def _centro(pk: int) -> CentroCosto:
    return get_object_or_404(CentroCosto, pk=pk, es_franquicia=False)


@requiere_operador_mvp
def plan(request: HttpRequest, centro_pk: int) -> HttpResponse:
    centro = _centro(centro_pk)
    exigir_acceso_centro(request.user, centro)
    fecha_parametro = request.GET.get("fecha")
    try:
        fecha = date.fromisoformat(fecha_parametro) if fecha_parametro else None
    except ValueError:
        return HttpResponseBadRequest(
            "La fecha histórica debe usar el formato AAAA-MM-DD."
        )
    sugerencias = obligaciones_sugeridas(centro)
    cambios = cambios_del_plan(centro, hasta=fecha)
    fecha_estado = fecha or timezone.localdate()
    if fecha is None:
        obligaciones = {obligacion.pk: obligacion for obligacion in sugerencias}
    else:
        obligaciones = {
            cambio.obligacion_id: cambio.obligacion
            for cambio in cambios
        }
    # Las obligaciones de titular trabajador entran al plan del centro por la
    # dotación, no por un cambio de aplicabilidad del centro: el centro no es
    # su titular, pero sí la vista de trabajo donde se ven.
    for obligacion in obligaciones_de_la_dotacion(centro, en_fecha=fecha):
        obligaciones.setdefault(obligacion.pk, obligacion)
    # La dotación se lee una vez y se comparte entre todas las obligaciones del
    # plan: resolverla por obligación son cientos de consultas por pantalla.
    dotacion = leer_dotacion(en_fecha=fecha)
    items = [
        {
            "obligacion": obligacion,
            "cambio": estado_actual(centro, obligacion, hasta=fecha),
            "caso": caso_de_cumplimiento(
                centro=centro,
                obligacion=obligacion,
                en_fecha=fecha_estado,
                dotacion=dotacion,
            ),
        }
        for obligacion in obligaciones.values()
        if puede_acceder_version_evidencia(request.user, obligacion.version_actual)
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


@requiere_operador_mvp
def desglose(
    request: HttpRequest,
    centro_pk: int,
    obligacion_pk: int,
) -> HttpResponse:
    """Quiénes son las personas que hay detrás del estado agregado."""
    centro = _centro(centro_pk)
    exigir_acceso_centro(request.user, centro)
    obligacion = get_object_or_404(Obligacion, pk=obligacion_pk)
    exigir_acceso_version_evidencia(request.user, obligacion.version_actual)
    fecha_parametro = request.GET.get("fecha")
    try:
        fecha = date.fromisoformat(fecha_parametro) if fecha_parametro else None
    except ValueError:
        return HttpResponseBadRequest(
            "La fecha histórica debe usar el formato AAAA-MM-DD."
        )
    fecha_estado = fecha or timezone.localdate()
    return render(
        request,
        "planes_aplicacion/desglose.html",
        {
            "centro": centro,
            "obligacion": obligacion,
            "fecha": fecha,
            "agregado": caso_de_cumplimiento(
                centro=centro,
                obligacion=obligacion,
                en_fecha=fecha_estado,
            ),
            "casos": casos_de_la_dotacion(
                centro=centro,
                obligacion=obligacion,
                en_fecha=fecha_estado,
            ),
        },
    )


@requiere_modificador_mvp
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
                contexto=ContextoBitacora.para_plan(centro),
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
                contexto=ContextoBitacora.para_plan(centro, obligacion),
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


@requiere_modificador_mvp
def agregar(request: HttpRequest, centro_pk: int) -> HttpResponse:
    return _cambiar(request, centro_pk, aplica=True)


@requiere_modificador_mvp
def no_aplica(request: HttpRequest, centro_pk: int) -> HttpResponse:
    return _cambiar(request, centro_pk, aplica=False)
