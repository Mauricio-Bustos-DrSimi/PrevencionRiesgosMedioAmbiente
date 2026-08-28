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
from obligaciones.forms import FormularioCierre, FormularioObligacion
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion


Parametros = ParamSpec("Parametros")
Respuesta = TypeVar("Respuesta", bound=HttpResponse)


def requiere_operador(
    vista: Callable[Parametros, Respuesta],
) -> Callable[Parametros, Respuesta]:
    @login_required
    @wraps(vista)
    def protegida(*args: Parametros.args, **kwargs: Parametros.kwargs) -> Respuesta:
        request = cast(HttpRequest, args[0])
        usuario = request.user
        if not (
            usuario.is_superuser
            or usuario.groups.filter(name="Prevencionista").exists()
        ):
            raise PermissionDenied
        return vista(*args, **kwargs)

    return protegida


@requiere_operador
def catalogo(request: HttpRequest) -> HttpResponse:
    obligaciones_vigentes = [
        obligacion
        for obligacion in Obligacion.objects.prefetch_related("versiones").all()
        if obligacion.esta_vigente
    ]
    return render(
        request,
        "obligaciones/catalogo.html",
        {"obligaciones": obligaciones_vigentes},
    )


@requiere_operador
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
                tipos_centro=formulario.cleaned_data["tipos_centro"],
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
                obligacion=obligacion,
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/formulario.html",
        {"formulario": formulario, "titulo": "Registrar obligación"},
    )


@requiere_operador
def detalle(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(
        Obligacion.objects.prefetch_related("versiones__autor"),
        pk=pk,
    )
    return render(
        request,
        "obligaciones/detalle.html",
        {"obligacion": obligacion, "version_actual": obligacion.version_actual},
    )


@requiere_operador
def corregir(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(Obligacion, pk=pk)
    actual = obligacion.version_actual
    if not obligacion.esta_vigente:
        raise PermissionDenied
    datos_iniciales = {
        "nombre": actual.nombre,
        "norma_origen": actual.norma_origen,
        "titular": actual.titular,
        "periodicidad": actual.periodicidad,
        "tipos_centro": actual.tipos_centro,
    }
    formulario = FormularioObligacion(request.POST or None, initial=datos_iniciales)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            obligacion = Obligacion.objects.select_for_update().get(pk=pk)
            actual = obligacion.version_actual
            if not obligacion.esta_vigente:
                raise PermissionDenied
            version = VersionObligacion.objects.create(
                obligacion=obligacion,
                numero=actual.numero + 1,
                nombre=formulario.cleaned_data["nombre"],
                norma_origen=formulario.cleaned_data["norma_origen"],
                titular=formulario.cleaned_data["titular"],
                periodicidad=formulario.cleaned_data["periodicidad"],
                tipos_centro=formulario.cleaned_data["tipos_centro"],
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
                obligacion=obligacion,
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/formulario.html",
        {"formulario": formulario, "titulo": "Corregir obligación"},
    )


@requiere_operador
def cerrar(request: HttpRequest, pk: int) -> HttpResponse:
    obligacion = get_object_or_404(Obligacion, pk=pk)
    actual = obligacion.version_actual
    if not obligacion.esta_vigente:
        raise PermissionDenied
    formulario = FormularioCierre(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        actor = cast(User, request.user)
        with transaction.atomic():
            obligacion = Obligacion.objects.select_for_update().get(pk=pk)
            actual = obligacion.version_actual
            if not obligacion.esta_vigente:
                raise PermissionDenied
            version = VersionObligacion.objects.create(
                obligacion=obligacion,
                numero=actual.numero + 1,
                nombre=actual.nombre,
                norma_origen=actual.norma_origen,
                titular=actual.titular,
                periodicidad=actual.periodicidad,
                tipos_centro=actual.tipos_centro,
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
                obligacion=obligacion,
            )
        return redirect("obligaciones:detalle", pk=obligacion.pk)
    return render(
        request,
        "obligaciones/cierre.html",
        {"formulario": formulario, "obligacion": obligacion},
    )
