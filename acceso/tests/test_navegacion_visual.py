import os
from copy import deepcopy
from typing import Any, cast
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path, resolve, reverse

from acceso.context_processors import contexto_visual
from acceso.permisos import requiere_operador_mvp
from configuracion.urls import urlpatterns as rutas_aplicacion


PLANTILLA_NAVEGACION = """
{% extends "layouts/aplicacion.html" %}
{% block title %}Resumen de prueba{% endblock %}
{% block content %}<p>Contenido ficticio.</p>{% endblock %}
"""

CONFIGURACION_TEMPLATES = cast(
    list[dict[str, Any]],
    deepcopy(settings.TEMPLATES),
)
CONFIGURACION_TEMPLATES[0]["APP_DIRS"] = False
CONFIGURACION_TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.locmem.Loader",
        {"pruebas/navegacion.html": PLANTILLA_NAVEGACION},
    ),
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]


@requiere_operador_mvp
def navegacion_de_prueba(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pruebas/navegacion.html",
        {"titulo_pagina": "Resumen de prueba"},
    )


urlpatterns = [
    path("_pruebas/navegacion/", navegacion_de_prueba, name="navegacion-prueba"),
    *rutas_aplicacion,
]


@override_settings(
    ROOT_URLCONF=__name__,
    TEMPLATES=CONFIGURACION_TEMPLATES,
)
class NavegacionVisualTests(TestCase):
    def setUp(self) -> None:
        self.grupo_prevencionista = Group.objects.get(name="Prevencionista")

    def crear_usuario(
        self,
        nombre: str,
        *,
        prevencionista: bool = False,
        sysadmin: bool = False,
    ) -> User:
        usuario = get_user_model().objects.create_user(
            username=nombre,
            password="clave-segura-de-prueba",
            is_superuser=sysadmin,
            is_staff=sysadmin,
        )
        if prevencionista:
            usuario.groups.add(self.grupo_prevencionista)
        return usuario

    def test_anonimo_es_redirigido_y_usuario_sin_rol_recibe_403(self) -> None:
        anonimo = self.client.get("/_pruebas/navegacion/")
        usuario = self.crear_usuario("sin_rol")
        self.client.force_login(usuario)
        sin_rol = self.client.get("/_pruebas/navegacion/")

        self.assertRedirects(
            anonimo,
            "/cuentas/iniciar-sesion/?next=/_pruebas/navegacion/",
            fetch_redirect_response=False,
        )
        self.assertEqual(sin_rol.status_code, 403)

    def test_prevencionista_ve_operacion_y_gestion_sin_administracion(self) -> None:
        usuario = self.crear_usuario("prevencionista", prevencionista=True)
        self.client.force_login(usuario)

        respuesta = self.client.get("/_pruebas/navegacion/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            '<span class="topbar__title">Resumen de prueba</span>',
        )
        self.assertContains(respuesta, "<h1>Resumen de prueba</h1>")
        for texto in (
            "Prevención de Riesgos y Medio Ambiente",
            "Inicio",
            "Cumplimiento",
            "Vencimientos",
            "Pendientes de validación",
            "Centros de costo",
            "Trabajadores",
            "Catálogo de obligaciones",
            "prevencionista",
            "Prevencionista",
        ):
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, reverse("admin:index"))
        self.assertNotContains(respuesta, reverse("importaciones:importar"))
        for nombre_url in (
            "inicio",
            "evidencias:operacion",
            "evidencias:vencimientos",
            "evidencias:pendientes",
            "centros_costo:lista",
            "trabajadores:lista",
            "obligaciones:catalogo",
        ):
            self.assertContains(respuesta, f'href="{reverse(nombre_url)}"')

    def test_sysadmin_ve_administracion_e_importaciones_sin_rol_inventado(self) -> None:
        usuario = self.crear_usuario("sysadmin", sysadmin=True)
        self.client.force_login(usuario)

        respuesta = self.client.get("/_pruebas/navegacion/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sysadmin")
        self.assertContains(respuesta, reverse("admin:index"))
        self.assertContains(respuesta, reverse("importaciones:importar"))
        self.assertNotContains(respuesta, '<span class="topbar__rol">Prevencionista</span>')

    def test_usuario_con_ambas_capacidades_ve_ambos_roles(self) -> None:
        usuario = self.crear_usuario(
            "ambos_roles",
            prevencionista=True,
            sysadmin=True,
        )
        self.client.force_login(usuario)

        respuesta = self.client.get("/_pruebas/navegacion/")

        self.assertContains(respuesta, '<span class="topbar__rol">Prevencionista</span>')
        self.assertContains(respuesta, '<span class="topbar__rol">Sysadmin</span>')

    def test_entorno_demo_se_muestra_solo_para_valor_exacto_demo(self) -> None:
        usuario = self.crear_usuario("operador_demo", prevencionista=True)
        self.client.force_login(usuario)

        with patch.dict(os.environ, {"DJANGO_ENTORNO": "demo"}):
            demo = self.client.get("/_pruebas/navegacion/")
        with patch.dict(os.environ, {"DJANGO_ENTORNO": "produccion"}):
            produccion = self.client.get("/_pruebas/navegacion/")

        self.assertContains(demo, "DEMOSTRACIÓN")
        self.assertNotContains(produccion, "DEMOSTRACIÓN")

    def test_sidebar_marca_la_ruta_actual_y_omite_planes_y_bitacora(self) -> None:
        usuario = self.crear_usuario("operador_activo", prevencionista=True)
        request = RequestFactory().get("/evidencias/operacion/")
        request.user = usuario
        request.resolver_match = resolve(
            "/evidencias/operacion/",
            urlconf="configuracion.urls",
        )

        contenido = render_to_string("includes/sidebar.html", request=request)

        self.assertIn(
            f'href="{reverse("evidencias:operacion")}" aria-current="page"',
            contenido,
        )
        self.assertIn('role="group" aria-labelledby="nav-operacion"', contenido)
        self.assertIn('role="group" aria-labelledby="nav-gestion"', contenido)
        self.assertNotIn("planes-aplicacion", contenido)
        self.assertNotIn("bitacora", contenido)

    def test_capacidades_se_calculan_una_vez_por_peticion(self) -> None:
        usuario = self.crear_usuario(
            "capacidades",
            prevencionista=True,
            sysadmin=True,
        )
        request = RequestFactory().get("/")
        request.user = usuario
        request.resolver_match = resolve("/", urlconf="configuracion.urls")

        with self.assertNumQueries(1):
            contexto = contexto_visual(request)

        self.assertEqual(contexto["roles_visuales"], ("Prevencionista", "Sysadmin"))
        self.assertTrue(contexto["capacidades"]["puede_validar_evidencias"])
        self.assertTrue(contexto["capacidades"]["puede_administrar"])

    def test_titulo_de_barra_identifica_las_areas_derivadas(self) -> None:
        request = RequestFactory().get("/evidencias/vencimientos/")
        request.user = AnonymousUser()
        request.resolver_match = resolve(
            "/evidencias/vencimientos/",
            urlconf="configuracion.urls",
        )

        contexto = contexto_visual(request)

        self.assertEqual(contexto["titulo_barra"], "Vencimientos")
