import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


ARCHIVOS_CSS = (
    "prevencion/css/tokens.css",
    "prevencion/css/base.css",
    "prevencion/css/layout.css",
    "prevencion/css/componentes.css",
    "prevencion/css/dashboard.css",
)
LOGOTIPO = "prevencion/img/logo-institucional.png"

TOKENS_APROBADOS = {
    "color-sidebar": "#12343B",
    "color-sidebar-text": "#F8FAFC",
    "color-sidebar-active": "#245563",
    "color-page": "#F4F6F8",
    "color-surface": "#FFFFFF",
    "color-text": "#182A32",
    "color-muted": "#52636D",
    "color-border": "#D7E0E5",
    "color-control-border": "#647782",
    "color-primary": "#155E75",
    "color-primary-hover": "#164E63",
    "color-focus": "#1D4ED8",
    "color-vigente": "#166534",
    "bg-vigente": "#DCFCE7",
    "color-por-vencer": "#854D0E",
    "bg-por-vencer": "#FEF3C7",
    "color-vencido": "#B91C1C",
    "bg-vencido": "#FEE2E2",
    "color-pendiente": "#1E40AF",
    "bg-pendiente": "#DBEAFE",
    "color-sin-evidencia": "#6B21A8",
    "bg-sin-evidencia": "#F3E8FF",
    "color-no-aplica": "#475569",
    "bg-no-aplica": "#F1F5F9",
    "space-1": "4px",
    "space-2": "8px",
    "space-3": "12px",
    "space-4": "16px",
    "space-5": "24px",
    "space-6": "32px",
    "space-7": "40px",
    "space-8": "48px",
    "radius-control": "6px",
    "radius-card": "12px",
    "radius-pill": "999px",
    "shadow-card": "0 2px 8px rgb(15 23 42 / 6%)",
    "sidebar-width": "240px",
    "topbar-min-height": "80px",
    "font-body": 'system-ui, -apple-system, "Segoe UI", sans-serif',
    "font-size-body": "16px",
    "font-size-table": "14px",
    "font-size-small": "13px",
    "font-size-h1": "28px",
    "font-size-h2": "20px",
    "font-size-kpi": "32px",
    "line-height-body": "1.5",
}

PARES_DE_CONTRASTE = {
    "texto sobre superficie": ("color-text", "color-surface"),
    "texto sobre fondo general": ("color-text", "color-page"),
    "sidebar": ("color-sidebar-text", "color-sidebar"),
    "Vigente": ("color-vigente", "bg-vigente"),
    "Por vencer": ("color-por-vencer", "bg-por-vencer"),
    "Vencido": ("color-vencido", "bg-vencido"),
    "Pendiente de validación": ("color-pendiente", "bg-pendiente"),
    "Sin evidencia": ("color-sin-evidencia", "bg-sin-evidencia"),
    "No aplica": ("color-no-aplica", "bg-no-aplica"),
}


def _contenido_estatico(ruta: str) -> str:
    encontrada = finders.find(ruta)
    if not isinstance(encontrada, str):
        raise AssertionError(f"No se encontró un único archivo estático: {ruta}")
    return Path(encontrada).read_text(encoding="utf-8")


def _luminancia(color: str) -> float:
    canales = [int(color[indice : indice + 2], 16) / 255 for indice in (1, 3, 5)]
    lineales = [
        canal / 12.92
        if canal <= 0.04045
        else ((canal + 0.055) / 1.055) ** 2.4
        for canal in canales
    ]
    return 0.2126 * lineales[0] + 0.7152 * lineales[1] + 0.0722 * lineales[2]


def _contraste(primer_color: str, segundo_color: str) -> float:
    clara, oscura = sorted(
        (_luminancia(primer_color), _luminancia(segundo_color)), reverse=True
    )
    return (clara + 0.05) / (oscura + 0.05)


class ArchivosEstaticosTests(SimpleTestCase):
    def test_django_resuelve_todos_los_recursos_del_ticket(self) -> None:
        for ruta in (*ARCHIVOS_CSS, LOGOTIPO):
            with self.subTest(ruta=ruta):
                self.assertIsInstance(finders.find(ruta), str)

    def test_tokens_coinciden_exactamente_con_la_especificacion(self) -> None:
        contenido = _contenido_estatico("prevencion/css/tokens.css")
        encontrados = dict(
            re.findall(r"--([a-z0-9-]+):\s*([^;]+);", contenido, flags=re.IGNORECASE)
        )

        self.assertEqual(encontrados, TOKENS_APROBADOS)

    def test_css_no_depende_de_recursos_externos_ni_javascript(self) -> None:
        patron_externo = re.compile(
            r"(?:https?:|(?<!:)//|@import)", flags=re.IGNORECASE
        )
        for ruta in ARCHIVOS_CSS:
            with self.subTest(ruta=ruta):
                contenido = _contenido_estatico(ruta)
                self.assertIsNone(patron_externo.search(contenido))
                self.assertNotIn("javascript:", contenido.lower())
                self.assertNotIn("bootstrap", contenido.lower())
                self.assertNotIn("tailwind", contenido.lower())

    def test_estados_tienen_clases_con_color_fondo_y_senal_adicional(self) -> None:
        contenido = _contenido_estatico("prevencion/css/componentes.css")
        for estado in (
            "vigente",
            "por-vencer",
            "vencido",
            "pendiente",
            "sin-evidencia",
            "no-aplica",
        ):
            with self.subTest(estado=estado):
                bloque = re.search(
                    rf"\.estado--{estado}\s*\{{(?P<reglas>[^}}]+)\}}",
                    contenido,
                )
                if bloque is None:
                    self.fail(f"Falta la clase visual para el estado {estado}")
                reglas = bloque.group("reglas")
                self.assertIn("color:", reglas)
                self.assertIn("background:", reglas)
        self.assertIn("border-inline-start-width: 4px", contenido)

    def test_los_seis_estados_pueden_dar_acento_a_kpi_y_barras(self) -> None:
        componentes = _contenido_estatico("prevencion/css/componentes.css")
        dashboard = _contenido_estatico("prevencion/css/dashboard.css")
        for estado in (
            "vigente",
            "por-vencer",
            "vencido",
            "pendiente",
            "sin-evidencia",
            "no-aplica",
        ):
            with self.subTest(estado=estado):
                self.assertRegex(
                    componentes,
                    rf"\.estado-color--{estado}\s*\{{[^}}]*color:",
                )
        self.assertIn("fill: currentColor", dashboard)

    def test_foco_visible_cumple_grosor_y_separacion_acordados(self) -> None:
        base = _contenido_estatico("prevencion/css/base.css")
        layout = _contenido_estatico("prevencion/css/layout.css")

        self.assertRegex(
            base,
            r":focus-visible\s*\{[^}]*outline:\s*3px solid var\(--color-focus\)"
            r"[^}]*outline-offset:\s*2px",
        )
        self.assertRegex(
            layout,
            r"\.app-sidebar :focus-visible\s*\{[^}]*"
            r"outline-color:\s*var\(--color-sidebar-text\)",
        )
        self.assertRegex(
            base,
            r"\.saltar-contenido:focus\s*\{[^}]*"
            r"outline-color:\s*var\(--color-surface\)",
        )
        self.assertGreaterEqual(
            _contraste(
                TOKENS_APROBADOS["color-surface"],
                TOKENS_APROBADOS["color-sidebar"],
            ),
            3,
        )

    def test_contraste_de_texto_alcanza_4_5_a_1(self) -> None:
        for nombre, (texto, fondo) in PARES_DE_CONTRASTE.items():
            with self.subTest(combinacion=nombre):
                proporcion = _contraste(
                    TOKENS_APROBADOS[texto], TOKENS_APROBADOS[fondo]
                )
                self.assertGreaterEqual(proporcion, 4.5)
