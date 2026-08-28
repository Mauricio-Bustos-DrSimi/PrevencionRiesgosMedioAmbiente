from typing import cast

from django.contrib.auth.models import User
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from acceso.permisos import requiere_operador_mvp
from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion
from planes_aplicacion.services import estado_actual

from .forms import EvidenciaForm
from .models import Evidencia
from .services import (
    ErrorCargaEvidencia,
    ErrorValidacionEvidencia,
    cargar_evidencia,
    casos_de_cumplimiento,
    EstadoCumplimiento,
    estado_de_evidencia,
    validar_evidencia,
    verificar_integridad_archivo,
)


ESTADOS_POR_FILTRO = {
    "vigente": EstadoCumplimiento.VIGENTE,
    "por_vencer": EstadoCumplimiento.POR_VENCER,
    "vencido": EstadoCumplimiento.VENCIDO,
    "pendiente_validacion": EstadoCumplimiento.PENDIENTE_VALIDACION,
    "sin_evidencia": EstadoCumplimiento.SIN_EVIDENCIA,
    "no_aplica": EstadoCumplimiento.NO_APLICA,
}


@requiere_operador_mvp
def operacion(request: HttpRequest) -> HttpResponse:
    centros = CentroCosto.objects.filter(es_franquicia=False)
    cantidad_centros = centros.count()
    cantidad_farmacias = centros.filter(tipo=CentroCosto.Tipo.FARMACIA).count()
    cantidad_administrativos = centros.filter(
        tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO
    ).count()
    cantidad_bodegas = centros.filter(tipo=CentroCosto.Tipo.BODEGA).count()
    piloto_conforme = (
        8 <= cantidad_centros <= 10
        and cantidad_farmacias >= 2
        and cantidad_administrativos == 1
        and cantidad_bodegas == 1
    )
    estado_seleccionado = request.GET.get("estado", "")
    estado = ESTADOS_POR_FILTRO.get(estado_seleccionado)
    tipo_centro = request.GET.get("tipo_centro", "")
    if tipo_centro not in CentroCosto.Tipo.values:
        tipo_centro = ""
    obligacion_parametro = request.GET.get("obligacion", "")
    try:
        obligacion_pk = int(obligacion_parametro)
    except ValueError:
        obligacion_pk = None
    casos = casos_de_cumplimiento(en_fecha=timezone.localdate())
    casos = [
        caso
        for caso in casos
        if (estado is None or caso.estado == estado)
        and (not tipo_centro or caso.centro.tipo == tipo_centro)
        and (obligacion_pk is None or caso.obligacion.pk == obligacion_pk)
    ]
    return render(
        request,
        "evidencias/operacion.html",
        {
            "casos": casos,
            "cantidad_centros": cantidad_centros,
            "piloto_conforme": piloto_conforme,
            "estado_seleccionado": estado_seleccionado,
            "estados": ESTADOS_POR_FILTRO.items(),
            "tipo_centro_seleccionado": tipo_centro,
            "tipos_centro": CentroCosto.Tipo.choices,
            "obligacion_seleccionada": obligacion_pk,
            "obligaciones": Obligacion.objects.prefetch_related("versiones").all(),
        },
    )


@requiere_operador_mvp
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


@requiere_operador_mvp
def pendientes(request: HttpRequest) -> HttpResponse:
    evidencias = Evidencia.objects.filter(
        validacion__isnull=True,
    ).select_related("centro_costo", "obligacion")
    return render(
        request,
        "evidencias/pendientes.html",
        {"evidencias": evidencias},
    )


@requiere_operador_mvp
def vencimientos(request: HttpRequest) -> HttpResponse:
    estados_por_filtro = {
        clave: ESTADOS_POR_FILTRO[clave]
        for clave in (
            "vencido",
            "por_vencer",
            "sin_evidencia",
            "pendiente_validacion",
        )
    }
    estado_seleccionado = request.GET.get("estado", "")
    if estado_seleccionado in estados_por_filtro:
        estados_visibles = {estados_por_filtro[estado_seleccionado]}
    else:
        estados_visibles = {
            EstadoCumplimiento.POR_VENCER,
            EstadoCumplimiento.VENCIDO,
        }
    tipo_centro = request.GET.get("tipo_centro", "")
    if tipo_centro not in CentroCosto.Tipo.values:
        tipo_centro = ""
    obligacion_parametro = request.GET.get("obligacion", "")
    try:
        obligacion_pk = int(obligacion_parametro)
    except ValueError:
        obligacion_pk = None
    casos = [
        caso
        for caso in casos_de_cumplimiento(en_fecha=timezone.localdate())
        if caso.estado in estados_visibles
        and (not tipo_centro or caso.centro.tipo == tipo_centro)
        and (obligacion_pk is None or caso.obligacion.pk == obligacion_pk)
    ]
    return render(
        request,
        "evidencias/vencimientos.html",
        {
            "casos": casos,
            "dias_por_vencer": settings.DIAS_POR_VENCER,
            "estado_seleccionado": estado_seleccionado,
            "tipo_centro_seleccionado": tipo_centro,
            "tipos_centro": CentroCosto.Tipo.choices,
            "obligacion_seleccionada": obligacion_pk,
            "obligaciones": Obligacion.objects.prefetch_related("versiones").all(),
        },
    )


@requiere_operador_mvp
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
    historial = Evidencia.objects.filter(
        centro_costo=evidencia.centro_costo,
        obligacion=evidencia.obligacion,
    ).select_related("validacion")
    cambio = estado_actual(evidencia.centro_costo, evidencia.obligacion)
    estado = estado_de_evidencia(
        evidencia,
        en_fecha=timezone.localdate(),
    )
    return render(
        request,
        "evidencias/validar.html",
        {
            "evidencia": evidencia,
            "validacion": validacion,
            "estado": estado,
            "error": error,
            "historial": historial,
            "puede_renovar": cambio is not None and cambio.aplica,
        },
    )


@requiere_operador_mvp
def verificar_integridad(request: HttpRequest, evidencia_pk: int) -> HttpResponse:
    evidencia = get_object_or_404(
        Evidencia.objects.select_related("centro_costo", "obligacion"),
        pk=evidencia_pk,
    )
    resultado = verificar_integridad_archivo(evidencia)
    if resultado.error:
        descripcion = resultado.error
    elif resultado.coincide:
        descripcion = "Coincidió con el hash SHA-256 registrado."
    else:
        descripcion = "No coincidió con el hash SHA-256 registrado."
    registrar_evento(
        actor=request.user,
        accion="verificar_integridad",
        entidad="Evidencia",
        identificador=str(evidencia.pk),
        descripcion=descripcion,
        canal="web",
        contexto=ContextoBitacora.para_evidencia(evidencia),
    )
    return render(
        request,
        "evidencias/integridad.html",
        {"evidencia": evidencia, "resultado": resultado},
    )
