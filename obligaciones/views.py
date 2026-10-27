from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render

from acceso.permisos import (
    exigir_acceso_version_evidencia,
    puede_acceder_version_evidencia,
    requiere_modificador_mvp,
    requiere_operador_mvp,
)
from bitacora.registro import ContextoBitacora, registrar_evento
from obligaciones.forms import FormularioCierre, FormularioObligacion
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion


@requiere_operador_mvp
def catalogo(request: HttpRequest) -> HttpResponse:
    obligaciones_vigentes = [
        obligacion
        for obligacion in Obligacion.objects.prefetch_related("versiones").all()
        if obligacion.esta_vigente
        and puede_acceder_version_evidencia(request.user, obligacion.version_actual)
    ]
    return render(
        request,
        "obligaciones/catalogo.html",
        {"obligaciones": obligaciones_vigentes},
    )


@requiere_modificador_mvp
def crear(request: HttpRequest) -> HttpResponse:
    formulario = FormularioObligacion(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            obligacion = Obligacion.objects.create()
            version = VersionObligacion.objects.create(
                obligacion=obligacion,
                numero=1,
                nombre=formulario.cleaned_data["nombre"],
                norma_origen=formulario.cleaned_data["norma_origen"],
                titular=formulario.cleaned_data["titular"],
                periodicidad=formulario.cleaned_data["periodicidad"],
                clasificacion_evidencia=formulario.cleaned_data[
                    "clasificacion_evidencia"
                ],
                tipos_centro=formulario.cleaned_data["tipos_centro"],
                cargos_sugeridos=formulario.cleaned_data["cargos_sugeridos"],
                tipo_version=TipoVersion.ALTA,
                autor=actor,
                motivo=formulario.cleaned_data["motivo"],
            )
            registrar_evento(
                actor=actor,
                accion="alta",
                entidad="obligación",
                identificador=str(obligacion.pk),
                descripcion=f"Se registró {version.nombre}.",
                canal="web",
                contexto=ContextoBitacora.para_obligacion(obligacion),
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/formulario.html",
        {"formulario": formulario, "titulo": "Registrar obligación"},
    )


@requiere_operador_mvp
def detalle(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(
        Obligacion.objects.prefetch_related("versiones__autor"),
        pk=pk,
    )
    exigir_acceso_version_evidencia(request.user, obligacion.version_actual)
    return render(
        request,
        "obligaciones/detalle.html",
        {"obligacion": obligacion, "version_actual": obligacion.version_actual},
    )


@requiere_modificador_mvp
def corregir(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(Obligacion, pk=pk)
    actual = obligacion.version_actual
    exigir_acceso_version_evidencia(request.user, actual)
    if not obligacion.esta_vigente:
        raise PermissionDenied
    datos_iniciales = {
        "nombre": actual.nombre,
        "norma_origen": actual.norma_origen,
        "titular": actual.titular,
        "periodicidad": actual.periodicidad,
        "clasificacion_evidencia": actual.clasificacion_evidencia,
        "tipos_centro": actual.tipos_centro,
        "cargos_sugeridos": "\n".join(actual.cargos_sugeridos),
    }
    datos_formulario: QueryDict | None = request.POST if request.method == "POST" else None
    if request.method == "POST" and "clasificacion_evidencia" not in request.POST:
        datos_compatibles = request.POST.copy()
        datos_compatibles["clasificacion_evidencia"] = actual.clasificacion_evidencia
        datos_formulario = datos_compatibles
    formulario = FormularioObligacion(datos_formulario, initial=datos_iniciales)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            obligacion = Obligacion.objects.select_for_update().get(pk=pk)
            actual = obligacion.version_actual
            exigir_acceso_version_evidencia(request.user, actual)
            if not obligacion.esta_vigente:
                raise PermissionDenied
            version = VersionObligacion.objects.create(
                obligacion=obligacion,
                numero=actual.numero + 1,
                nombre=formulario.cleaned_data["nombre"],
                norma_origen=formulario.cleaned_data["norma_origen"],
                titular=formulario.cleaned_data["titular"],
                periodicidad=formulario.cleaned_data["periodicidad"],
                clasificacion_evidencia=formulario.cleaned_data[
                    "clasificacion_evidencia"
                ],
                tipos_centro=formulario.cleaned_data["tipos_centro"],
                cargos_sugeridos=formulario.cleaned_data["cargos_sugeridos"],
                tipo_version=TipoVersion.CORRECCION,
                autor=actor,
                motivo=formulario.cleaned_data["motivo"],
            )
            registrar_evento(
                actor=actor,
                accion="corrección",
                entidad="obligación",
                identificador=str(obligacion.pk),
                descripcion=f"Se creó la versión {version.numero} de {version.nombre}.",
                canal="web",
                contexto=ContextoBitacora.para_obligacion(obligacion),
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/formulario.html",
        {"formulario": formulario, "titulo": "Corregir obligación"},
    )


@requiere_modificador_mvp
def cerrar(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(Obligacion, pk=pk)
    actual = obligacion.version_actual
    exigir_acceso_version_evidencia(request.user, actual)
    if not obligacion.esta_vigente:
        raise PermissionDenied
    formulario = FormularioCierre(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            obligacion = Obligacion.objects.select_for_update().get(pk=pk)
            actual = obligacion.version_actual
            exigir_acceso_version_evidencia(request.user, actual)
            if not obligacion.esta_vigente:
                raise PermissionDenied
            version = VersionObligacion.objects.create(
                obligacion=obligacion,
                numero=actual.numero + 1,
                nombre=actual.nombre,
                norma_origen=actual.norma_origen,
                titular=actual.titular,
                periodicidad=actual.periodicidad,
                clasificacion_evidencia=actual.clasificacion_evidencia,
                tipos_centro=actual.tipos_centro,
                cargos_sugeridos=actual.cargos_sugeridos,
                tipo_version=TipoVersion.CIERRE,
                fecha_cierre=formulario.cleaned_data["fecha_cierre"],
                autor=actor,
                motivo=formulario.cleaned_data["motivo"],
            )
            registrar_evento(
                actor=actor,
                accion="cierre",
                entidad="obligación",
                identificador=str(obligacion.pk),
                descripcion=f"Se cerró {version.nombre} el {version.fecha_cierre}.",
                canal="web",
                contexto=ContextoBitacora.para_obligacion(obligacion),
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/cierre.html",
        {"formulario": formulario, "obligacion": obligacion},
    )
