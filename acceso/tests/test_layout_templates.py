from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.test import SimpleTestCase, override_settings
from django.urls import path

from configuracion.urls import urlpatterns as rutas_aplicacion


PLANTILLA_MINIMA = """
{% extends "layouts/aplicacion.html" %}
{% block title %}Página de prueba{% endblock %}
{% block page_title %}Página de prueba{% endblock %}
{% block page_actions %}
  <a href="{% url 'layout-prueba' %}">Acción de prueba</a>
{% endblock %}
{% block content %}
  <p>Contenido ficticio para validar el layout.</p>
  {% include "includes/estado_cumplimiento.html" with estado="Vigente" only %}
  {% include "includes/estado_vacio.html" with titulo="Sin resultados" mensaje="No existen resultados ficticios." only %}
  <form method="post" action="{% url 'layout-prueba' %}" enctype="multipart/form-data">
    {% csrf_token %}
    <button type="submit">Enviar prueba</button>
  </form>
{% endblock %}
"""

CONFIGURACION_TEMPLATES = cast(
    list[dict[str, Any]], deepcopy(settings.TEMPLATES)
)
CONFIGURACION_TEMPLATES[0]["APP_DIRS"] = False
CONFIGURACION_TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.locmem.Loader",
        {"pruebas/layout_minimo.html": PLANTILLA_MINIMA},
    ),
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]


def layout_de_prueba(request: HttpRequest) -> HttpResponse:
    messages.info(request, "Mensaje ficticio conservado por el layout.")
    return render(request, "pruebas/layout_minimo.html")


urlpatterns = [
    path("prueba-layout/", layout_de_prueba, name="layout-prueba"),
    *rutas_aplicacion,
]


class AnalizadorEstructural(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cantidad: dict[str, int] = {}
        self.ids: set[str] = set()
        self.enlace_salto: str | None = None
        self.estilos: list[str] = []
        self.formularios: list[dict[str, str | None]] = []
        self.inputs: list[dict[str, str | None]] = []

    def handle_starttag(
        self, etiqueta: str, atributos: list[tuple[str, str | None]]
    ) -> None:
        atributos_dict = dict(atributos)
        self.cantidad[etiqueta] = self.cantidad.get(etiqueta, 0) + 1
        if identificador := atributos_dict.get("id"):
            self.ids.add(identificador)
        clases = atributos_dict.get("class") or ""
        if etiqueta == "a" and "saltar-contenido" in clases:
            self.enlace_salto = atributos_dict.get("href")
        if etiqueta == "link" and atributos_dict.get("rel") == "stylesheet":
            href = atributos_dict.get("href")
            if href:
                self.estilos.append(href)
        if etiqueta == "form":
            self.formularios.append(atributos_dict)
        if etiqueta == "input":
            self.inputs.append(atributos_dict)


@override_settings(
    ROOT_URLCONF=__name__,
    TEMPLATES=CONFIGURACION_TEMPLATES,
)
class LayoutCompartidoTests(SimpleTestCase):
    def test_template_heredado_produce_un_documento_accesible(self) -> None:
        respuesta = self.client.get("/prueba-layout/")
        contenido = respuesta.content.decode()
        analizador = AnalizadorEstructural()
        analizador.feed(contenido)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(analizador.cantidad.get("html"), 1)
        self.assertEqual(analizador.cantidad.get("body"), 1)
        self.assertEqual(analizador.cantidad.get("main"), 1)
        self.assertEqual(analizador.cantidad.get("h1"), 1)
        self.assertEqual(analizador.enlace_salto, "#contenido-principal")
        self.assertIn("contenido-principal", analizador.ids)
        self.assertContains(respuesta, '<html lang="es">')
        self.assertContains(respuesta, '<meta charset="utf-8">')
        self.assertContains(respuesta, 'name="viewport"')
        self.assertContains(respuesta, "Página de prueba")

    def test_base_carga_los_cinco_css_del_ticket_uno_sin_scripts(self) -> None:
        respuesta = self.client.get("/prueba-layout/")
        analizador = AnalizadorEstructural()
        analizador.feed(respuesta.content.decode())

        self.assertEqual(
            analizador.estilos,
            [
                "/static/prevencion/css/tokens.css",
                "/static/prevencion/css/base.css",
                "/static/prevencion/css/layout.css",
                "/static/prevencion/css/componentes.css",
                "/static/prevencion/css/dashboard.css",
            ],
        )
        self.assertNotIn("<script", respuesta.content.decode().lower())

    def test_layout_conserva_mensajes_formulario_csrf_metodo_y_url(self) -> None:
        respuesta = self.client.get("/prueba-layout/")
        analizador = AnalizadorEstructural()
        analizador.feed(respuesta.content.decode())

        self.assertContains(respuesta, "Mensaje ficticio conservado por el layout.")
        self.assertEqual(len(analizador.formularios), 1)
        self.assertEqual(analizador.formularios[0].get("method"), "post")
        self.assertEqual(
            analizador.formularios[0].get("enctype"), "multipart/form-data"
        )
        self.assertEqual(analizador.formularios[0].get("action"), "/prueba-layout/")
        self.assertTrue(
            any(
                campo.get("name") == "csrfmiddlewaretoken"
                for campo in analizador.inputs
            )
        )

    def test_includes_son_fragmentos_y_muestran_texto_semantico(self) -> None:
        respuesta = self.client.get("/prueba-layout/")

        self.assertContains(respuesta, 'class="estado estado--vigente"')
        self.assertContains(respuesta, ">Vigente<")
        self.assertContains(respuesta, "Sin resultados")
        self.assertContains(respuesta, "No existen resultados ficticios.")
        for nombre in ("estado_cumplimiento.html", "estado_vacio.html"):
            contenido = (
                Path(settings.BASE_DIR) / "templates" / "includes" / nombre
            ).read_text(encoding="utf-8")
            with self.subTest(template=nombre):
                self.assertNotRegex(
                    contenido.lower(), r"<(?:!doctype|html|body|main)\b"
                )
