import re
from datetime import date
from html import unescape
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from centros_costo.models import CentroCosto
from evidencias.services import EstadoCumplimiento

from acceso.dashboard import resumir_casos


class ResumenDashboardTests(TestCase):
    def test_separa_los_seis_estados_por_tipo_de_titular(self) -> None:
        centro = SimpleNamespace(pk=1)
        trabajador = SimpleNamespace(pk=10)
        casos = []
        for estado in EstadoCumplimiento:
            casos.extend(
                [
                    SimpleNamespace(centro=centro, estado=estado, trabajador=None),
                    SimpleNamespace(
                        centro=centro,
                        estado=estado,
                        trabajador=trabajador,
                    ),
                ]
            )
        casos.append(
            SimpleNamespace(
                centro=centro,
                estado=EstadoCumplimiento.VENCIDO,
                trabajador=trabajador,
            )
        )

        resumen = resumir_casos(casos)

        self.assertEqual(len(resumen.distribuciones), 2)
        for distribucion in resumen.distribuciones:
            self.assertEqual(len(distribucion.barras), 6)
        vencidas = resumen.kpis[0]
        self.assertEqual(vencidas.etiqueta, "Vencidas")
        self.assertEqual(vencidas.cantidad_centros, 1)
        self.assertEqual(vencidas.cantidad_trabajadores, 2)
        self.assertEqual(resumen.maximo, 2)

    def test_resumen_vacio_no_divide_por_cero(self) -> None:
        resumen = resumir_casos([])

        self.assertEqual(resumen.maximo, 0)
        self.assertTrue(
            all(
                barra.ancho == 0
                for distribucion in resumen.distribuciones
                for barra in distribucion.barras
            )
        )


class DashboardHttpTests(TestCase):
    fecha = date(2026, 9, 9)

    def setUp(self) -> None:
        self.grupo = Group.objects.get(name="Prevencionista")
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencion_dashboard",
            password="clave-segura-de-prueba",
        )
        self.prevencionista.groups.add(self.grupo)
        self.farmacia = CentroCosto.objects.create(
            codigo_contable="FAR-DASH-001",
            nombre="Farmacia Dashboard",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        self.bodega = CentroCosto.objects.create(
            codigo_contable="BOD-DASH-001",
            nombre="Bodega Dashboard",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.trabajador = SimpleNamespace(
            pk=50,
            nombre="Nombre privado no visible",
            rut="12345678-5",
        )

    def _casos(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                centro=self.farmacia,
                estado=EstadoCumplimiento.VENCIDO,
                trabajador=None,
            ),
            SimpleNamespace(
                centro=self.farmacia,
                estado=EstadoCumplimiento.VENCIDO,
                trabajador=self.trabajador,
            ),
            SimpleNamespace(
                centro=self.farmacia,
                estado=EstadoCumplimiento.SIN_EVIDENCIA,
                trabajador=self.trabajador,
            ),
            SimpleNamespace(
                centro=self.farmacia,
                estado=EstadoCumplimiento.PENDIENTE_VALIDACION,
                trabajador=None,
            ),
            SimpleNamespace(
                centro=self.bodega,
                estado=EstadoCumplimiento.POR_VENCER,
                trabajador=None,
            ),
            SimpleNamespace(
                centro=self.bodega,
                estado=EstadoCumplimiento.VIGENTE,
                trabajador=self.trabajador,
            ),
            SimpleNamespace(
                centro=self.bodega,
                estado=EstadoCumplimiento.NO_APLICA,
                trabajador=None,
            ),
        ]

    def _dotacion(self) -> SimpleNamespace:
        return SimpleNamespace(
            personas={self.trabajador.pk: self.trabajador},
            centros={self.trabajador.pk: self.farmacia},
            validados=frozenset({self.trabajador.pk}),
        )

    def test_portada_filtra_una_lista_y_no_expone_personas(self) -> None:
        self.client.force_login(self.prevencionista)
        url = reverse("inicio")
        consulta = f"{url}?centro={self.farmacia.pk}&tipo_centro=farmacia"

        with (
            patch("acceso.views.timezone.localdate", return_value=self.fecha) as reloj,
            patch("acceso.views.casos_de_cumplimiento", return_value=self._casos()) as servicio,
            patch("acceso.views.leer_dotacion", return_value=self._dotacion()) as dotacion,
        ):
            with CaptureQueriesContext(connection) as consultas:
                respuesta = self.client.get(consulta)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "acceso/inicio.html")
        reloj.assert_called_once_with()
        servicio.assert_called_once_with(en_fecha=self.fecha)
        dotacion.assert_called_once_with(en_fecha=self.fecha)
        self.assertEqual(len(consultas), 5)
        self.assertContains(respuesta, "09/09/2026")
        self.assertContains(respuesta, "Vencidas")
        self.assertContains(respuesta, "Sin evidencia")
        self.assertContains(respuesta, "Pendientes de validación")
        self.assertContains(respuesta, "Por vencer")
        self.assertContains(
            respuesta,
            '<strong class="numero-tabular">1</strong> instalación operable filtrada',
            html=True,
        )
        self.assertContains(
            respuesta,
            '<strong class="numero-tabular">1</strong> trabajador validado con asignación vigente',
            html=True,
        )
        self.assertNotContains(respuesta, self.trabajador.nombre)
        self.assertNotContains(respuesta, self.trabajador.rut)
        self.assertEqual(respuesta.context["kpis"][3].cantidad_centros, 0)

        contenido = respuesta.content.decode()
        coincidencia = re.search(
            r'href="([^"]+)" aria-label="1 instalaciones: Vencidas"',
            contenido,
        )
        if coincidencia is None:
            self.fail("No se encontró el enlace del KPI de instalaciones vencidas.")
        enlace = urlparse(unescape(coincidencia.group(1)))
        self.assertEqual(enlace.path, reverse("evidencias:operacion"))
        self.assertEqual(
            parse_qs(enlace.query),
            {
                "estado": ["vencido"],
                "titular": ["centro_costo"],
                "centro": [str(self.farmacia.pk)],
                "tipo_centro": ["farmacia"],
            },
        )

    def test_muestra_distribuciones_tabla_y_cero_resultados(self) -> None:
        self.client.force_login(self.prevencionista)
        with (
            patch("acceso.views.timezone.localdate", return_value=self.fecha),
            patch("acceso.views.casos_de_cumplimiento", return_value=self._casos()),
            patch("acceso.views.leer_dotacion", return_value=self._dotacion()),
        ):
            respuesta = self.client.get("/?centro=999999")

        self.assertContains(respuesta, "Distribución actual por estado")
        self.assertContains(respuesta, "Obligaciones de instalaciones")
        self.assertContains(respuesta, "Obligaciones por trabajador")
        self.assertContains(respuesta, "<caption>", count=2)
        self.assertContains(respuesta, 'scope="col"', count=4)
        self.assertContains(respuesta, 'width="0"', count=12)
        self.assertContains(respuesta, "Sin casos en este alcance")
        self.assertContains(respuesta, "0 instalaciones")
        self.assertContains(respuesta, "0 trabajadores")
        self.assertNotContains(respuesta, "nan")

    def test_acciones_rapidas_respetan_capacidad_de_validacion(self) -> None:
        casos: list[SimpleNamespace] = []
        self.client.force_login(self.prevencionista)
        with (
            patch("acceso.views.casos_de_cumplimiento", return_value=casos),
            patch("acceso.views.leer_dotacion", return_value=self._dotacion()),
        ):
            prevencion = self.client.get("/")
        self.assertContains(prevencion, "Validar evidencias")
        self.assertContains(prevencion, reverse("trabajadores:crear"))

        sysadmin: User = get_user_model().objects.create_superuser(
            username="sysadmin_dashboard",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)
        with (
            patch("acceso.views.casos_de_cumplimiento", return_value=casos),
            patch("acceso.views.leer_dotacion", return_value=self._dotacion()),
        ):
            administracion = self.client.get("/")
        self.assertNotContains(administracion, "Validar evidencias")
        self.assertContains(administracion, reverse("trabajadores:crear"))
        self.assertNotContains(administracion, "<script")
