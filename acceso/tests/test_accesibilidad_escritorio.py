from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


def _css(ruta: str) -> str:
    archivo = finders.find(ruta)
    if not isinstance(archivo, str):
        raise AssertionError(f"No se encontró el recurso estático {ruta}.")
    return Path(archivo).read_text(encoding="utf-8")


class ReflujoEscritorioTests(SimpleTestCase):
    def test_el_zoom_200_refluye_sin_ocultar_sidebar_ni_columnas(self) -> None:
        layout = _css("prevencion/css/layout.css")
        componentes = _css("prevencion/css/componentes.css")
        dashboard = _css("prevencion/css/dashboard.css")

        self.assertRegex(layout, r"@media\s*\(max-width:\s*900px\)")
        self.assertRegex(
            layout,
            r"\.app-topbar\s*\{[^}]*flex-wrap:\s*wrap",
        )
        self.assertRegex(
            componentes,
            r"\.filtros__campos\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)",
        )
        self.assertRegex(
            dashboard,
            r"\.kpi-grid,[^}]*\.distribucion-estados\s*\{[^}]*"
            r"grid-template-columns:\s*minmax\(0,\s*1fr\)",
        )
        self.assertNotRegex(
            layout,
            r"\.app-sidebar\s*\{[^}]*(display:\s*none|visibility:\s*hidden)",
        )

    def test_el_scroll_horizontal_queda_contenido_en_las_tablas(self) -> None:
        base = _css("prevencion/css/base.css")
        layout = _css("prevencion/css/layout.css")

        self.assertRegex(
            layout,
            r"\.app-shell\s*\{[^}]*grid-template-columns:\s*"
            r"var\(--sidebar-width\)\s+minmax\(0,\s*1fr\)",
        )
        self.assertRegex(
            layout,
            r"\.tabla-desplazable\s*\{[^}]*overflow-x:\s*auto",
        )
        self.assertNotRegex(base + layout, r"(?:html|body)\s*\{[^}]*overflow-x:\s*hidden")


class AdminSinRedisenioTests(TestCase):
    def test_el_admin_no_carga_el_layout_de_la_aplicacion(self) -> None:
        administrador = get_user_model().objects.create_superuser(
            username="admin_ticket7",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(administrador)

        respuesta = self.client.get(reverse("admin:index"))

        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertNotIn("prevencion/css/", contenido)
        self.assertNotIn('class="app-shell"', contenido)
