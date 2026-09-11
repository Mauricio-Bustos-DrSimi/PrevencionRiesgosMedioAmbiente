from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.test import SimpleTestCase, override_settings
from django.urls import path, reverse

from configuracion.urls import urlpatterns as rutas_aplicacion


PLANTILLA_COMPONENTES = """
{% extends "layouts/aplicacion.html" %}
{% block title %}Componentes compartidos{% endblock %}
{% block content %}
  {% include "includes/tarjeta_kpi.html" with etiqueta="Vencidas" variante="vencido" cantidad_centros=3 cantidad_trabajadores=2 url_centros="/casos/centros/" url_trabajadores="/casos/trabajadores/" only %}
  {% include "evidencias/includes/filtros_operacion.html" %}
  <form class="formulario tarjeta" method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <div class="campo">
      <label for="archivo-evidencia">Evidencia</label>
      <input id="archivo-evidencia" name="archivo" type="file" aria-describedby="ayuda-archivo error-archivo" aria-invalid="true">
      <span class="ayuda-campo" id="ayuda-archivo">Formato PDF.</span>
      <span class="error-campo" id="error-archivo">Debe seleccionar un archivo.</span>
    </div>
    <div class="formulario__acciones"><button class="boton boton--primario" type="submit">Enviar</button></div>
  </form>
  <div class="tabla-desplazable" tabindex="0" aria-label="Resultados de prueba">
    <table class="tabla-datos tabla-datos--ancha">
      <caption>Obligaciones filtradas</caption>
      <thead><tr><th scope="col">Centro</th><th scope="col">Obligación</th><th scope="col">Estado</th></tr></thead>
      <tbody><tr><td>FAR-001</td><td>Control ficticio</td><td>Vencido</td></tr></tbody>
    </table>
  </div>
{% endblock %}
"""

CONFIGURACION_TEMPLATES = cast(
    list[dict[str, Any]],
    deepcopy(settings.TEMPLATES),
)
CONFIGURACION_TEMPLATES[0]["APP_DIRS"] = False
CONFIGURACION_TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.locmem.Loader",
        {"pruebas/componentes.html": PLANTILLA_COMPONENTES},
    ),
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]


def componentes_de_prueba(request: HttpRequest) -> HttpResponse:
    def identificador(nombre: str) -> int | None:
        try:
            return int(request.GET.get(nombre, ""))
        except ValueError:
            return None

    messages.success(request, "Operación completada.")
    messages.info(request, "Información disponible.")
    messages.warning(request, "Revise el vencimiento.")
    messages.error(request, '<script>alert("mensaje")</script>')
    return render(
        request,
        "pruebas/componentes.html",
        {
            "titulo_pagina": "Componentes compartidos",
            "estados": (("vigente", "Vigente"), ("vencido", "Vencido")),
            "estado_seleccionado": request.GET.get("estado", ""),
            "tipos_centro": (("farmacia", "Farmacia"), ("bodega", "Bodega")),
            "tipo_centro_seleccionado": request.GET.get("tipo_centro", ""),
            "obligaciones": (
                SimpleNamespace(
                    pk=9,
                    version_actual=SimpleNamespace(nombre="Control documental"),
                ),
            ),
            "obligacion_seleccionada": identificador("obligacion"),
            "centros": (SimpleNamespace(pk=7, codigo_contable="BOD-007"),),
            "centro_seleccionado": identificador("centro"),
            "trabajadores": (
                SimpleNamespace(pk=5, nombre="Persona ficticia", rut="12345678-5"),
            ),
            "trabajador_seleccionado": identificador("trabajador"),
        },
    )


urlpatterns = [
    path("_pruebas/componentes/", componentes_de_prueba, name="componentes-prueba"),
    *rutas_aplicacion,
]


@override_settings(ROOT_URLCONF=__name__, TEMPLATES=CONFIGURACION_TEMPLATES)
class ComponentesCompartidosTests(SimpleTestCase):
    def test_mensajes_tienen_estilo_rol_y_escape_segun_nivel(self) -> None:
        respuesta = self.client.get("/_pruebas/componentes/")

        self.assertContains(
            respuesta,
            '<p class="mensaje mensaje--exito" role="status">Operación completada.</p>',
            html=True,
        )
        self.assertContains(
            respuesta,
            '<p class="mensaje mensaje--informacion" role="status">Información disponible.</p>',
            html=True,
        )
        self.assertContains(
            respuesta,
            '<p class="mensaje mensaje--aviso" role="status">Revise el vencimiento.</p>',
            html=True,
        )
        self.assertContains(respuesta, 'class="mensaje mensaje--error" role="alert"')
        self.assertContains(respuesta, "&lt;script&gt;alert")
        self.assertNotContains(respuesta, '<script>alert("mensaje")</script>')

    def test_filtros_conservan_nombres_seleccion_y_accion_limpiar(self) -> None:
        respuesta = self.client.get(
            "/_pruebas/componentes/"
            "?estado=vencido&tipo_centro=bodega&obligacion=9&centro=7&trabajador=5"
        )

        self.assertContains(
            respuesta,
            f'<form class="filtros tarjeta" method="get" action="{reverse("evidencias:operacion")}" aria-labelledby="filtros-operacion-titulo">',
        )
        for nombre in ("estado", "tipo_centro", "obligacion", "centro", "trabajador"):
            self.assertContains(respuesta, f'name="{nombre}"')
        for valor in ("vencido", "bodega", "9", "7", "5"):
            self.assertContains(respuesta, f'value="{valor}" selected')
        self.assertContains(respuesta, "Persona ficticia (••.•••.678-5)")
        self.assertNotContains(respuesta, "12345678-5")
        self.assertContains(
            respuesta,
            f'href="{reverse("evidencias:operacion")}"',
        )
        self.assertContains(respuesta, ">Limpiar<")

    def test_formulario_preserva_post_multipart_csrf_y_descripciones(self) -> None:
        respuesta = self.client.get("/_pruebas/componentes/")

        self.assertContains(respuesta, 'method="post"')
        self.assertContains(respuesta, 'enctype="multipart/form-data"')
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, 'label for="archivo-evidencia"')
        self.assertContains(
            respuesta,
            'aria-describedby="ayuda-archivo error-archivo"',
        )
        self.assertContains(respuesta, 'aria-invalid="true"')

    def test_tabla_tiene_caption_encabezados_y_contenedor_enfocable(self) -> None:
        respuesta = self.client.get("/_pruebas/componentes/")

        self.assertContains(
            respuesta,
            '<div class="tabla-desplazable" tabindex="0" aria-label="Resultados de prueba">',
        )
        self.assertContains(respuesta, "<caption>Obligaciones filtradas</caption>")
        self.assertContains(respuesta, 'scope="col"', count=3)

    def test_tarjeta_kpi_separa_titulares_y_sus_enlaces(self) -> None:
        respuesta = self.client.get("/_pruebas/componentes/")

        self.assertContains(respuesta, "Vencidas")
        self.assertContains(respuesta, 'href="/casos/centros/"')
        self.assertContains(respuesta, 'href="/casos/trabajadores/"')
        self.assertContains(respuesta, "3 instalaciones")
        self.assertContains(respuesta, "2 trabajadores")
        self.assertNotContains(respuesta, "5 casos")
        self.assertNotContains(respuesta, "<script")
