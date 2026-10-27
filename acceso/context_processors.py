import os
from typing import TypedDict

from django.contrib.auth.models import User
from django.http import HttpRequest

from .permisos import GRUPO_ENCARGADO, GRUPO_PREVENCIONISTA


class CapacidadesVisuales(TypedDict):
    puede_operar: bool
    puede_validar_evidencias: bool
    puede_administrar: bool
    puede_importar: bool
    puede_modificar: bool
    puede_ver_pendientes: bool
    puede_descargar_evidencias: bool
    puede_ver_rut_completo: bool


class ContextoVisual(TypedDict):
    capacidades: CapacidadesVisuales
    roles_visuales: tuple[str, ...]
    seccion_activa: str
    entorno_demostracion: bool
    titulo_barra: str


def _seccion_activa(request: HttpRequest) -> str:
    coincidencia = request.resolver_match
    if coincidencia is None:
        return ""

    espacio = coincidencia.namespace or ""
    nombre = coincidencia.url_name or ""
    if nombre == "inicio":
        return "inicio"
    if espacio == "evidencias":
        if nombre in {"vencimientos", "pendientes"}:
            return nombre
        return "operacion"
    if espacio == "centros_costo":
        return "centros"
    if espacio == "trabajadores":
        return "trabajadores"
    if espacio == "obligaciones":
        return "obligaciones"
    if espacio == "importaciones":
        return "importaciones"
    if espacio == "admin":
        return "administracion"
    return ""


def _titulo_barra(request: HttpRequest) -> str:
    coincidencia = request.resolver_match
    if coincidencia is None:
        return "Prevención de Riesgos y Medio Ambiente"

    espacio = coincidencia.namespace or ""
    nombre = coincidencia.url_name or ""
    if nombre == "inicio":
        return "Resumen de cumplimiento"
    if espacio == "evidencias":
        return {
            "vencimientos": "Vencimientos",
            "pendientes": "Pendientes de validación",
        }.get(nombre, "Evidencias y cumplimiento")
    return {
        "centros_costo": "Centros de costo",
        "trabajadores": "Trabajadores",
        "obligaciones": "Catálogo de obligaciones",
        "planes_aplicacion": "Planes de aplicación",
        "importaciones": "Importaciones",
        "bitacora": "Trazabilidad",
        "admin": "Administración Django",
    }.get(espacio, "Prevención de Riesgos y Medio Ambiente")


def contexto_visual(request: HttpRequest) -> ContextoVisual:
    usuario = request.user
    administrador = False
    prevencionista = False
    encargado = False
    if usuario.is_authenticated:
        actor: User = usuario
        administrador = actor.is_superuser
        grupos = set(actor.groups.values_list("name", flat=True))
        prevencionista = GRUPO_PREVENCIONISTA in grupos
        encargado = GRUPO_ENCARGADO in grupos

    roles: list[str] = []
    if administrador:
        roles.append("Administrador")
    if prevencionista:
        roles.append("Prevencionista")
    if encargado:
        roles.append("Encargado")

    capacidades: CapacidadesVisuales = {
        "puede_operar": administrador or prevencionista or encargado,
        "puede_validar_evidencias": administrador or prevencionista,
        "puede_administrar": administrador,
        "puede_importar": administrador or prevencionista,
        "puede_modificar": administrador or prevencionista,
        "puede_ver_pendientes": administrador or prevencionista,
        "puede_descargar_evidencias": administrador or prevencionista,
        "puede_ver_rut_completo": administrador or prevencionista,
    }
    return {
        "capacidades": capacidades,
        "roles_visuales": tuple(roles),
        "seccion_activa": _seccion_activa(request),
        "entorno_demostracion": os.environ.get("DJANGO_ENTORNO") == "demo",
        "titulo_barra": _titulo_barra(request),
    }
