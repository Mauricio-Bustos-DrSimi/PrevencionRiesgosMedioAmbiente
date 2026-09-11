from typing import cast

from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from acceso.permisos import requiere_operador_mvp
from bitacora.registro import ContextoBitacora, registrar_evento
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TitularObligacion
from planes_aplicacion.services import estado_actual, estado_actual_trabajador
from trabajadores.models import Trabajador
from trabajadores.services import dotacion_del_centro

from .forms import CorreccionEvidenciaForm, EvidenciaForm, ValidacionEvidenciaForm
from .filtros import ESTADOS_POR_FILTRO, FiltroOperativo
from .models import Evidencia
from .services import (
    CasoCumplimiento,
    ErrorCargaEvidencia,
    ErrorCorreccionEvidencia,
    ErrorValidacionEvidencia,
    EstadoCumplimiento,
    FechasLeidas,
    RechazoCargaEvidencia,
    cargar_evidencia,
    casos_de_cumplimiento,
    corregir_evidencia,
    estado_de_evidencia,
    fechas_efectivas,
    validar_evidencia,
    verificar_integridad_archivo,
)


def _dotacion_como_consulta(centro: CentroCosto) -> QuerySet[Trabajador]:
    dotacion = dotacion_del_centro(centro)
    return Trabajador.objects.filter(
        pk__in=[trabajador.pk for trabajador in dotacion]
    )


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
    filtro = FiltroOperativo.desde(request, incluir_titular=True)
    casos = [
        caso
        for caso in casos_de_cumplimiento(en_fecha=timezone.localdate())
        if (estado is None or caso.estado == estado) and filtro.admite(caso)
    ]
    return render(
        request,
        "evidencias/operacion.html",
        {
            "titulo_pagina": "Operación del piloto",
            "casos": casos,
            "cantidad_centros": cantidad_centros,
            "piloto_conforme": piloto_conforme,
            "estado_seleccionado": estado_seleccionado,
            "estados": ESTADOS_POR_FILTRO.items(),
        }
        | filtro.como_contexto(),
    )


@requiere_operador_mvp
def cargar(request: HttpRequest, centro_pk: int, obligacion_pk: int) -> HttpResponse:
    centro = get_object_or_404(CentroCosto, pk=centro_pk, es_franquicia=False)
    obligacion = get_object_or_404(Obligacion, pk=obligacion_pk)
    version = obligacion.version_actual
    es_del_trabajador = version.titular == TitularObligacion.TRABAJADOR
    dotacion = _dotacion_como_consulta(centro) if es_del_trabajador else None
    formulario = EvidenciaForm(
        request.POST or None,
        request.FILES or None,
        dotacion=dotacion,
    )
    contexto = {
        "formulario": formulario,
        "centro": centro,
        "obligacion": obligacion,
        "es_del_trabajador": es_del_trabajador,
    }
    if not es_del_trabajador:
        cambio = estado_actual(centro, obligacion)
        if cambio is None or not cambio.aplica:
            return render(
                request,
                "evidencias/formulario.html",
                contexto
                | {"error": "No aplica: no se puede cargar esta evidencia."},
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
                trabajador=formulario.cleaned_data.get("trabajador"),
            )
        except RechazoCargaEvidencia as exc:
            return render(
                request,
                "evidencias/formulario.html",
                contexto | {"error": str(exc)},
                status=403,
            )
        except ErrorCargaEvidencia as exc:
            return render(
                request,
                "evidencias/formulario.html",
                contexto | {"error": str(exc)},
            )
        return render(
            request,
            "evidencias/cargada.html",
            {"centro": centro, "obligacion": obligacion, "evidencia": evidencia},
        )
    return render(request, "evidencias/formulario.html", contexto | {"error": None})


@requiere_operador_mvp
def pendientes(request: HttpRequest) -> HttpResponse:
    evidencias = Evidencia.objects.filter(
        validacion__isnull=True,
    ).select_related("centro_costo", "obligacion", "trabajador")
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
    filtro = FiltroOperativo.desde(request)
    casos = [
        caso
        for caso in casos_de_cumplimiento(en_fecha=timezone.localdate())
        if caso.estado in estados_visibles and filtro.admite(caso)
    ]
    return render(
        request,
        "evidencias/vencimientos.html",
        {
            "casos": casos,
            "dias_por_vencer": settings.DIAS_POR_VENCER,
            "estado_seleccionado": estado_seleccionado,
        }
        | filtro.como_contexto(),
    )


def _evidencia_con_contexto(evidencia_pk: int) -> Evidencia:
    return get_object_or_404(
        Evidencia.objects.select_related(
            "centro_costo",
            "obligacion",
            "trabajador",
        ).prefetch_related("correcciones__autor"),
        pk=evidencia_pk,
    )


def _pantalla_de_validacion(
    request: HttpRequest,
    evidencia: Evidencia,
    *,
    formulario: ValidacionEvidenciaForm,
    correccion: CorreccionEvidenciaForm,
    error: str | None,
    estado_http: int = 200,
) -> HttpResponse:
    hoy = timezone.localdate()
    validacion = getattr(evidencia, "validacion", None)
    historial = Evidencia.objects.filter(
        centro_costo=evidencia.centro_costo,
        obligacion=evidencia.obligacion,
        trabajador=evidencia.trabajador,
    ).select_related("validacion")
    if evidencia.trabajador is not None:
        cambio = estado_actual_trabajador(evidencia.trabajador, evidencia.obligacion)
    else:
        cambio = estado_actual(evidencia.centro_costo, evidencia.obligacion)
    return render(
        request,
        "evidencias/validar.html",
        {
            "evidencia": evidencia,
            "validacion": validacion,
            "estado": estado_de_evidencia(evidencia, en_fecha=hoy),
            "error": error,
            "historial": historial,
            "puede_renovar": cambio is not None and cambio.aplica,
            "formulario": formulario,
            "formulario_correccion": correccion,
            "fechas": fechas_efectivas(evidencia),
            "correcciones": evidencia.correcciones.all(),
        },
        status=estado_http,
    )


@requiere_operador_mvp
def validar(request: HttpRequest, evidencia_pk: int) -> HttpResponse:
    evidencia = _evidencia_con_contexto(evidencia_pk)
    # Validar sin corregir se sigue enviando sin datos: el formulario se liga
    # al método, no a que el envío traiga algo.
    formulario = ValidacionEvidenciaForm(
        request.POST if request.method == "POST" else None
    )
    error = None
    if request.method == "POST":
        if formulario.is_valid():
            datos = formulario.cleaned_data
            correccion = (
                FechasLeidas(
                    fecha_emision=datos["fecha_emision"],
                    fecha_vencimiento=datos["fecha_vencimiento"],
                    motivo=datos["motivo"],
                )
                if datos["corregir_fechas"]
                else None
            )
            try:
                validar_evidencia(
                    evidencia=evidencia,
                    actor=cast(User, request.user),
                    correccion=correccion,
                )
            except (ErrorValidacionEvidencia, ErrorCorreccionEvidencia) as exc:
                error = str(exc)
            else:
                return redirect("evidencias:validar", evidencia_pk=evidencia.pk)
        evidencia = _evidencia_con_contexto(evidencia_pk)
    return _pantalla_de_validacion(
        request,
        evidencia,
        formulario=formulario,
        correccion=CorreccionEvidenciaForm(),
        error=error,
    )


@requiere_operador_mvp
def corregir(request: HttpRequest, evidencia_pk: int) -> HttpResponse:
    """Corregir es independiente de validar: también se corrige lo ya validado."""
    evidencia = _evidencia_con_contexto(evidencia_pk)
    formulario = CorreccionEvidenciaForm(request.POST or None)
    error = None
    if request.method == "POST" and formulario.is_valid():
        try:
            corregir_evidencia(
                evidencia=evidencia,
                actor=cast(User, request.user),
                fecha_emision=formulario.cleaned_data["fecha_emision"],
                fecha_vencimiento=formulario.cleaned_data["fecha_vencimiento"],
                motivo=formulario.cleaned_data["motivo"],
            )
        except ErrorCorreccionEvidencia as exc:
            error = str(exc)
        else:
            return redirect("evidencias:validar", evidencia_pk=evidencia.pk)
        evidencia = _evidencia_con_contexto(evidencia_pk)
    return _pantalla_de_validacion(
        request,
        evidencia,
        formulario=ValidacionEvidenciaForm(),
        correccion=formulario,
        error=error,
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
