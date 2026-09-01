from datetime import date
from typing import cast

from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from acceso.permisos import requiere_operador_mvp
from bitacora.registro import ContextoBitacora, registrar_evento
from evidencias.services import caso_de_trabajador
from planes_aplicacion.models import CambioAplicabilidad
from planes_aplicacion.services import (
    cambios_del_plan_trabajador,
    estado_actual_trabajador,
    obligaciones_sugeridas_trabajador,
)

from .forms import (
    AplicabilidadTrabajadorForm,
    MotivoForm,
    TrabajadorForm,
    TrasladoForm,
)
from .models import Trabajador
from .services import (
    ErrorDotacion,
    crear_trabajador,
    dar_de_baja_trabajador,
    trasladar_trabajador,
    validar_trabajador,
)


@requiere_operador_mvp
def lista(request: HttpRequest) -> HttpResponse:
    trabajadores = Trabajador.objects.all()
    return render(
        request,
        "trabajadores/lista.html",
        {
            "trabajadores": [
                {
                    "trabajador": trabajador,
                    "centro": trabajador.centro_costo_actual,
                    "validado": trabajador.esta_validado(),
                }
                for trabajador in trabajadores
            ]
        },
    )


@requiere_operador_mvp
def crear(request: HttpRequest) -> HttpResponse:
    formulario = TrabajadorForm(request.POST or None)
    error = None
    if request.method == "POST" and formulario.is_valid():
        try:
            trabajador = crear_trabajador(
                rut=formulario.cleaned_data["rut"],
                nombre=formulario.cleaned_data["nombre"],
                cargo=formulario.cleaned_data["cargo"],
                centro=formulario.cleaned_data["centro_costo"],
                motivo=formulario.cleaned_data["motivo"],
                actor=cast(User, request.user),
            )
        except ErrorDotacion as exc:
            error = str(exc)
        else:
            return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/formulario.html",
        {"formulario": formulario, "error": error, "titulo": "Registrar trabajador"},
    )


@requiere_operador_mvp
def detalle(request: HttpRequest, pk: int) -> HttpResponse:
    trabajador = get_object_or_404(Trabajador, pk=pk)
    fecha_parametro = request.GET.get("fecha")
    try:
        fecha = date.fromisoformat(fecha_parametro) if fecha_parametro else None
    except ValueError:
        return HttpResponseBadRequest(
            "La fecha histórica debe usar el formato AAAA-MM-DD."
        )
    fecha_estado = fecha or timezone.localdate()
    sugerencias = obligaciones_sugeridas_trabajador(trabajador)
    cambios = cambios_del_plan_trabajador(trabajador, hasta=fecha)
    obligaciones = {
        cambio.obligacion_id: cambio.obligacion for cambio in cambios
    }
    if fecha is None:
        for obligacion in sugerencias:
            obligaciones.setdefault(obligacion.pk, obligacion)
    items = [
        {
            "obligacion": obligacion,
            "cambio": estado_actual_trabajador(trabajador, obligacion, hasta=fecha),
            "caso": caso_de_trabajador(
                trabajador=trabajador,
                obligacion=obligacion,
                en_fecha=fecha_estado,
            ),
        }
        for obligacion in obligaciones.values()
    ]
    return render(
        request,
        "trabajadores/detalle.html",
        {
            "trabajador": trabajador,
            "centro": trabajador.centro_costo_en(fecha),
            "validado": trabajador.esta_validado(en_fecha=fecha),
            "de_baja": trabajador.esta_de_baja(en_fecha=fecha),
            "sugerencias": sugerencias,
            "items": items,
            "cambios": cambios,
            "asignaciones": trabajador.asignaciones.select_related(
                "centro_costo",
                "autor",
            ),
            "fecha": fecha,
        },
    )


@requiere_operador_mvp
def validar(request: HttpRequest, pk: int) -> HttpResponse:
    trabajador = get_object_or_404(Trabajador, pk=pk)
    error = None
    if request.method == "POST":
        try:
            validar_trabajador(
                trabajador=trabajador,
                actor=cast(User, request.user),
            )
        except ErrorDotacion as exc:
            error = str(exc)
        else:
            return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/motivo.html",
        {
            "trabajador": trabajador,
            "titulo": "Validar trabajador",
            "formulario": None,
            "error": error,
        },
    )


@requiere_operador_mvp
def trasladar(request: HttpRequest, pk: int) -> HttpResponse:
    trabajador = get_object_or_404(Trabajador, pk=pk)
    formulario = TrasladoForm(request.POST or None)
    error = None
    if request.method == "POST" and formulario.is_valid():
        try:
            trasladar_trabajador(
                trabajador=trabajador,
                centro=formulario.cleaned_data["centro_costo"],
                motivo=formulario.cleaned_data["motivo"],
                actor=cast(User, request.user),
            )
        except ErrorDotacion as exc:
            error = str(exc)
        else:
            return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/motivo.html",
        {
            "trabajador": trabajador,
            "titulo": "Trasladar trabajador",
            "formulario": formulario,
            "error": error,
        },
    )


@requiere_operador_mvp
def dar_de_baja(request: HttpRequest, pk: int) -> HttpResponse:
    trabajador = get_object_or_404(Trabajador, pk=pk)
    formulario = MotivoForm(request.POST or None)
    error = None
    if request.method == "POST" and formulario.is_valid():
        try:
            dar_de_baja_trabajador(
                trabajador=trabajador,
                motivo=formulario.cleaned_data["motivo"],
                actor=cast(User, request.user),
            )
        except ErrorDotacion as exc:
            error = str(exc)
        else:
            return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/motivo.html",
        {
            "trabajador": trabajador,
            "titulo": "Dar de baja al trabajador",
            "formulario": formulario,
            "error": error,
        },
    )


@requiere_operador_mvp
def confirmar_sugerencia(request: HttpRequest, pk: int) -> HttpResponse:
    """Confirma individualmente el plan que el cargo solo sugiere."""
    trabajador = get_object_or_404(Trabajador, pk=pk)
    formulario = MotivoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            for obligacion in obligaciones_sugeridas_trabajador(trabajador):
                if estado_actual_trabajador(trabajador, obligacion) is None:
                    CambioAplicabilidad.objects.create(
                        trabajador=trabajador,
                        obligacion=obligacion,
                        aplica=True,
                        motivo=formulario.cleaned_data["motivo"],
                        autor=actor,
                    )
            registrar_evento(
                actor=actor,
                accion="confirmar_sugerencia_trabajador",
                entidad="plan de aplicación",
                identificador=trabajador.rut,
                descripcion=(
                    f"Confirmó el plan individual de {trabajador.nombre} "
                    f"({trabajador.cargo})."
                ),
                canal="web",
                contexto=ContextoBitacora.para_trabajador(
                    trabajador,
                    trabajador.centro_costo_actual,
                ),
            )
        return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/motivo.html",
        {
            "trabajador": trabajador,
            "titulo": "Confirmar plan sugerido",
            "formulario": formulario,
            "error": None,
        },
    )


def _cambiar(request: HttpRequest, pk: int, *, aplica: bool) -> HttpResponse:
    trabajador = get_object_or_404(Trabajador, pk=pk)
    formulario = AplicabilidadTrabajadorForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        obligacion = formulario.cleaned_data["obligacion"]
        with transaction.atomic():
            CambioAplicabilidad.objects.create(
                trabajador=trabajador,
                obligacion=obligacion,
                aplica=aplica,
                motivo=formulario.cleaned_data["motivo"],
                autor=actor,
            )
            registrar_evento(
                actor=actor,
                accion="aplicar" if aplica else "declarar_no_aplica",
                entidad="plan de aplicación",
                identificador=trabajador.rut,
                descripcion=(
                    f"Actualizó la aplicabilidad de {obligacion} para "
                    f"{trabajador.nombre}."
                ),
                canal="web",
                contexto=ContextoBitacora.para_trabajador(
                    trabajador,
                    trabajador.centro_costo_actual,
                    obligacion,
                ),
            )
        return redirect("trabajadores:detalle", pk=trabajador.pk)
    return render(
        request,
        "trabajadores/motivo.html",
        {
            "trabajador": trabajador,
            "titulo": "Actualizar plan del trabajador",
            "formulario": formulario,
            "error": None,
        },
    )


@requiere_operador_mvp
def agregar(request: HttpRequest, pk: int) -> HttpResponse:
    return _cambiar(request, pk, aplica=True)


@requiere_operador_mvp
def no_aplica(request: HttpRequest, pk: int) -> HttpResponse:
    return _cambiar(request, pk, aplica=False)
