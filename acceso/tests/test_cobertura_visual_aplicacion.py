from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


PLANTILLAS_APLICACION = (
    "bitacora/recorrido.html",
    "centros_costo/detalle.html",
    "centros_costo/lista.html",
    "evidencias/cargada.html",
    "evidencias/formulario.html",
    "evidencias/integridad.html",
    "evidencias/pendientes.html",
    "evidencias/validar.html",
    "evidencias/vencimientos.html",
    "importaciones/importar.html",
    "obligaciones/catalogo.html",
    "obligaciones/cierre.html",
    "obligaciones/detalle.html",
    "obligaciones/formulario.html",
    "planes_aplicacion/desglose.html",
    "planes_aplicacion/motivo.html",
    "planes_aplicacion/plan.html",
    "trabajadores/detalle.html",
    "trabajadores/formulario.html",
    "trabajadores/lista.html",
    "trabajadores/motivo.html",
)


def _plantilla(ruta: str) -> str:
    return (Path(settings.BASE_DIR) / "templates" / ruta).read_text(
        encoding="utf-8"
    )


class CoberturaVisualAplicacionTests(SimpleTestCase):
    def test_todas_las_pantallas_autenticadas_heredan_el_layout(self) -> None:
        for ruta in PLANTILLAS_APLICACION:
            with self.subTest(plantilla=ruta):
                contenido = _plantilla(ruta)
                self.assertIn('{% extends "layouts/aplicacion.html" %}', contenido)
                self.assertNotIn("<!doctype", contenido.lower())
                self.assertNotIn("<html", contenido.lower())
                self.assertNotIn("<body", contenido.lower())
                self.assertNotIn("<main", contenido.lower())

    def test_tablas_comparten_semantica_y_desplazamiento_interno(self) -> None:
        for ruta in (
            "bitacora/recorrido.html",
            "centros_costo/lista.html",
            "evidencias/vencimientos.html",
            "evidencias/pendientes.html",
            "obligaciones/catalogo.html",
            "trabajadores/lista.html",
        ):
            with self.subTest(plantilla=ruta):
                contenido = _plantilla(ruta)
                self.assertIn('class="tabla-desplazable"', contenido)
                self.assertIn('class="tabla-datos', contenido)
                self.assertIn("<caption>", contenido)
                self.assertIn('scope="col"', contenido)

    def test_formularios_y_acciones_usan_componentes_compartidos(self) -> None:
        for ruta in PLANTILLAS_APLICACION:
            contenido = _plantilla(ruta)
            if "<form" not in contenido:
                continue
            with self.subTest(plantilla=ruta):
                self.assertRegex(contenido, r'<form[^>]+class="[^"]*(?:formulario|filtros)')
                self.assertRegex(contenido, r'class="boton boton--')

    def test_inicio_de_sesion_usa_la_base_sin_sidebar(self) -> None:
        contenido = _plantilla("registration/iniciar_sesion.html")
        self.assertIn('{% extends "base.html" %}', contenido)
        self.assertIn('class="pagina-acceso"', contenido)
        self.assertNotIn("<!doctype", contenido.lower())

    def test_desglose_por_persona_oculta_el_rut_del_listado(self) -> None:
        contenido = _plantilla("planes_aplicacion/desglose.html")
        self.assertIn("{% load presentacion %}", contenido)
        self.assertIn("caso.trabajador.rut|rut_oculto", contenido)
