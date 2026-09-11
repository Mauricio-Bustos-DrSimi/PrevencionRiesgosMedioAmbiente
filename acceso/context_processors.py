import os
from typing import TypedDict

from django.contrib.auth.models import User
from django.http import HttpRequest

from .permisos import GRUPO_PREVENCIONISTA


class CapacidadesVisuales(TypedDict):
    puede_operar: bool
    puede_validar_evidencias: bool
    puede_administrar: bool
    puede_importar: bool


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
    es_prevencionista = False
    es_sysadmin = False
    if usuario.is_authenticated:
        actor: User = usuario
        es_prevencionista = actor.groups.filter(
            name=GRUPO_PREVENCIONISTA,
        ).exists()
        es_sysadmin = actor.is_superuser

    roles: list[str] = []
    if es_prevencionista:
        roles.append("Prevencionista")
    if es_sysadmin:
        roles.append("Sysadmin")

    capacidades: CapacidadesVisuales = {
        "puede_operar": es_prevencionista or es_sysadmin,
        "puede_validar_evidencias": es_prevencionista,
        "puede_administrar": es_sysadmin,
        "puede_importar": es_sysadmin,
    }
    return {
        "capacidades": capacidades,
        "roles_visuales": tuple(roles),
        "seccion_activa": _seccion_activa(request),
        "entorno_demostracion": os.environ.get("DJANGO_ENTORNO") == "demo",
        "titulo_barra": _titulo_barra(request),
    }
