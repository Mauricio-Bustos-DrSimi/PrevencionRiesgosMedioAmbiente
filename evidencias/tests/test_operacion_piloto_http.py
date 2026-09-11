import re
import tempfile
from datetime import date, datetime
from html import unescape
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aceptacion.reloj import reloj_en
from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion
from planes_aplicacion.models import CambioAplicabilidad

from evidencias.models import Evidencia
from evidencias.services import EstadoCumplimiento
from trabajadores.services import crear_trabajador, validar_trabajador


# La bandeja se consulta a fechas absolutas; los actos que la alimentan tienen
# que quedar registrados en un momento igual de fijo.
JORNADA = timezone.make_aware(datetime(2026, 8, 28, 9, 0))


class OperacionPilotoHttpTests(TestCase):
    def setUp(self) -> None:
        reloj = reloj_en(JORNADA)
        reloj.__enter__()
        self.addCleanup(reloj.__exit__, None, None, None)
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_piloto",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(Group.objects.get(name="Prevencionista"))
        self.obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Mantener extintores vigentes",
            norma_origen="DS 594",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.usuario,
            motivo="Alta para operar el piloto",
        )
        self.client.force_login(self.usuario)

    def _crear_obligacion(self, nombre: str) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=nombre,
            norma_origen="DS 594",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.usuario,
            motivo="Alta para operar el piloto",
        )
        return obligacion

    def _incorporar_al_plan(
        self,
        centro: CentroCosto,
        obligacion: Obligacion | None = None,
    ) -> None:
        obligacion = obligacion or self.obligacion
        respuesta = self.client.post(
            reverse("planes_aplicacion:agregar", args=[centro.pk]),
            {
                "obligacion": str(obligacion.pk),
                "motivo": "Configuración del conjunto piloto",
            },
        )
        self.assertEqual(respuesta.status_code, 302)

    def test_muestra_nueve_centros_heterogeneos_y_excluye_franquicias(self) -> None:
        centros = [
            CentroCosto.objects.create(
                codigo_contable=f"FAR-PIL-{numero:03}",
                nombre=f"Farmacia Piloto {numero}",
                tipo=CentroCosto.Tipo.FARMACIA,
            )
            for numero in range(1, 8)
        ]
        centros.extend(
            [
                CentroCosto.objects.create(
                    codigo_contable="ADM-PIL-001",
                    nombre="Centro administrativo piloto",
                    tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
                ),
                CentroCosto.objects.create(
                    codigo_contable="BOD-PIL-001",
                    nombre="Bodega piloto",
                    tipo=CentroCosto.Tipo.BODEGA,
                ),
            ]
        )
        franquicia = CentroCosto.objects.create(
            codigo_contable="FRA-PIL-001",
            nombre="Franquicia fuera del piloto",
            tipo=CentroCosto.Tipo.FARMACIA,
            es_franquicia=True,
        )
        for centro in centros:
            self._incorporar_al_plan(centro)
        CambioAplicabilidad.objects.create(
            centro_costo=franquicia,
            obligacion=self.obligacion,
            aplica=True,
            motivo="Dato heredado que no debe entrar a la operación",
            autor=self.usuario,
        )

        respuesta = self.client.get(reverse("evidencias:operacion"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            '<p><strong class="numero-tabular">9</strong> centros de costo operables</p>',
            html=True,
        )
        self.assertContains(respuesta, "Piloto conforme")
        self.assertContains(respuesta, "Farmacia Piloto 1")
        self.assertContains(respuesta, "Centro administrativo piloto")
        self.assertContains(respuesta, "Bodega piloto")
        self.assertNotContains(respuesta, "Franquicia fuera del piloto")

    def test_no_declara_conforme_un_piloto_sin_varias_farmacias(self) -> None:
        CentroCosto.objects.create(
            codigo_contable="FAR-COMP-001",
            nombre="Única farmacia",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        CentroCosto.objects.create(
            codigo_contable="BOD-COMP-001",
            nombre="Bodega composición",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        for numero in range(1, 7):
            CentroCosto.objects.create(
                codigo_contable=f"ADM-COMP-{numero:03}",
                nombre=f"Centro administrativo {numero}",
                tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
            )

        respuesta = self.client.get(reverse("evidencias:operacion"))

        self.assertContains(
            respuesta,
            '<p><strong class="numero-tabular">8</strong> centros de costo operables</p>',
            html=True,
        )
        self.assertNotContains(respuesta, "Piloto conforme")
        self.assertContains(respuesta, "varias farmacias")

    def test_la_portada_abre_la_operacion_del_piloto(self) -> None:
        respuesta = self.client.get(reverse("inicio"))

        self.assertContains(respuesta, reverse("evidencias:operacion"))
        self.assertContains(respuesta, "Cumplimiento")

    def test_filtra_sin_confundir_sin_evidencia_vencido_y_pendiente(self) -> None:
        centro = CentroCosto.objects.create(
            codigo_contable="FAR-EST-001",
            nombre="Farmacia Estados",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        obligacion_vencida = self._crear_obligacion("Evidencia vencida única")
        obligacion_pendiente = self._crear_obligacion("Evidencia pendiente única")
        for obligacion in [
            self.obligacion,
            obligacion_vencida,
            obligacion_pendiente,
        ]:
            respuesta_plan = self.client.post(
                reverse("planes_aplicacion:agregar", args=[centro.pk]),
                {
                    "obligacion": str(obligacion.pk),
                    "motivo": "Configurar estados diferenciados",
                },
            )
            self.assertEqual(respuesta_plan.status_code, 302)

        evidencias = []
        for obligacion in [obligacion_vencida, obligacion_pendiente]:
            respuesta_carga = self.client.post(
                reverse("evidencias:cargar", args=[centro.pk, obligacion.pk]),
                {
                    "emisor": "Organismo certificador",
                    "fecha_emision": "2026-01-01",
                    "fecha_vencimiento": "2026-12-31",
                    "archivo": SimpleUploadedFile(
                        f"evidencia-{obligacion.pk}.pdf",
                        f"contenido {obligacion.pk}".encode(),
                        content_type="application/pdf",
                    ),
                },
            )
            self.assertEqual(respuesta_carga.status_code, 200)
            evidencia = Evidencia.objects.get(
                centro_costo=centro,
                obligacion=obligacion,
            )
            evidencias.append(evidencia)
        self.client.post(reverse("evidencias:validar", args=[evidencias[0].pk]))
        url = reverse("evidencias:operacion")

        with patch("evidencias.views.timezone.localdate", return_value=date(2027, 1, 1)):
            sin_evidencia = self.client.get(f"{url}?estado=sin_evidencia")
            vencido = self.client.get(f"{url}?estado=vencido")
            pendiente = self.client.get(f"{url}?estado=pendiente_validacion")

        url_sin_evidencia = reverse(
            "evidencias:cargar",
            args=[centro.pk, self.obligacion.pk],
        )
        url_vencida = reverse("evidencias:validar", args=[evidencias[0].pk])
        url_pendiente = reverse("evidencias:validar", args=[evidencias[1].pk])
        self.assertContains(sin_evidencia, url_sin_evidencia)
        self.assertNotContains(sin_evidencia, url_vencida)
        self.assertNotContains(sin_evidencia, url_pendiente)
        self.assertContains(vencido, url_vencida)
        self.assertNotContains(vencido, url_sin_evidencia)
        self.assertNotContains(vencido, url_pendiente)
        self.assertContains(pendiente, url_pendiente)
        self.assertNotContains(pendiente, url_sin_evidencia)
        self.assertNotContains(pendiente, url_vencida)

    def test_filtra_por_tipo_y_obligacion_con_navegacion_contextual(self) -> None:
        farmacia = CentroCosto.objects.create(
            codigo_contable="FAR-NAV-001",
            nombre="Farmacia Navegable",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        bodega = CentroCosto.objects.create(
            codigo_contable="BOD-NAV-001",
            nombre="Bodega Navegable",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self._incorporar_al_plan(farmacia)
        self._incorporar_al_plan(bodega)
        respuesta_carga = self.client.post(
            reverse("evidencias:cargar", args=[farmacia.pk, self.obligacion.pk]),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": "2026-08-01",
                "fecha_vencimiento": "2027-08-01",
                "archivo": SimpleUploadedFile(
                    "evidencia-navegable.pdf",
                    b"contenido navegable",
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(respuesta_carga.status_code, 200)
        evidencia = Evidencia.objects.get(
            centro_costo=farmacia,
            obligacion=self.obligacion,
        )
        url = reverse("evidencias:operacion")

        farmacia_filtrada = self.client.get(
            f"{url}?tipo_centro=farmacia&obligacion={self.obligacion.pk}"
        )
        bodega_filtrada = self.client.get(
            f"{url}?tipo_centro=bodega&obligacion={self.obligacion.pk}"
        )

        self.assertContains(farmacia_filtrada, "Farmacia Navegable")
        self.assertNotContains(farmacia_filtrada, "Bodega Navegable")
        self.assertContains(
            farmacia_filtrada,
            reverse("centros_costo:detalle", args=[farmacia.pk]),
        )
        self.assertContains(
            farmacia_filtrada,
            reverse("obligaciones:detalle", args=[self.obligacion.pk]),
        )
        self.assertContains(
            farmacia_filtrada,
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(bodega_filtrada, "Bodega Navegable")
        self.assertNotContains(bodega_filtrada, "Farmacia Navegable")
        self.assertContains(
            bodega_filtrada,
            reverse(
                "evidencias:cargar",
                args=[bodega.pk, self.obligacion.pk],
            ),
        )

    def test_muestra_vigente_y_no_aplica_como_estados_operables(self) -> None:
        centro = CentroCosto.objects.create(
            codigo_contable="FAR-COM-001",
            nombre="Farmacia Cumplimiento",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        obligacion_no_aplica = self._crear_obligacion("Control no aplicable")
        self._incorporar_al_plan(centro)
        respuesta_carga = self.client.post(
            reverse("evidencias:cargar", args=[centro.pk, self.obligacion.pk]),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": "2026-08-01",
                "fecha_vencimiento": "2027-08-01",
                "archivo": SimpleUploadedFile(
                    "evidencia-vigente.pdf",
                    b"contenido vigente",
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(respuesta_carga.status_code, 200)
        evidencia = Evidencia.objects.get(
            centro_costo=centro,
            obligacion=self.obligacion,
        )
        respuesta_validacion = self.client.post(
            reverse("evidencias:validar", args=[evidencia.pk])
        )
        self.assertEqual(respuesta_validacion.status_code, 302)
        respuesta_no_aplica = self.client.post(
            reverse("planes_aplicacion:no_aplica", args=[centro.pk]),
            {
                "obligacion": str(obligacion_no_aplica.pk),
                "motivo": "No corresponde a esta instalación",
            },
        )
        self.assertEqual(respuesta_no_aplica.status_code, 302)
        url = reverse("evidencias:operacion")

        with patch("evidencias.views.timezone.localdate", return_value=date(2026, 8, 28)):
            vigentes = self.client.get(f"{url}?estado=vigente")
            no_aplicables = self.client.get(f"{url}?estado=no_aplica")

        self.assertContains(
            vigentes,
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(no_aplicables, "Control no aplicable")
        self.assertContains(
            no_aplicables,
            reverse("planes_aplicacion:plan", args=[centro.pk]),
        )
        self.assertNotContains(
            no_aplicables,
            reverse(
                "evidencias:cargar",
                args=[centro.pk, obligacion_no_aplica.pk],
            ),
        )

    def test_migra_la_operacion_a_tabla_sin_cambiar_filtros_ni_enlaces(self) -> None:
        centro = CentroCosto.objects.create(
            codigo_contable="FAR-TAB-001",
            nombre="Farmacia de operación ficticia",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        trabajador = crear_trabajador(
            rut="12345678-5",
            nombre="Persona Ficticia de Operación",
            cargo="Cargo ficticio",
            centro=centro,
            motivo="Fixture visual de operación",
            actor=self.usuario,
        )
        validar_trabajador(
            trabajador=trabajador,
            actor=self.usuario,
        )
        obligacion_trabajador = self._crear_obligacion(
            "Obligación individual ficticia"
        )
        casos = [
            SimpleNamespace(
                centro=centro,
                obligacion=self.obligacion,
                nombre_obligacion="Mantener extintores vigentes",
                trabajador=None,
                estado=EstadoCumplimiento.SIN_EVIDENCIA,
                evidencia=None,
                fecha_fin=None,
            ),
            SimpleNamespace(
                centro=centro,
                obligacion=obligacion_trabajador,
                nombre_obligacion="Obligación individual ficticia",
                trabajador=trabajador,
                estado=EstadoCumplimiento.SIN_EVIDENCIA,
                evidencia=None,
                fecha_fin=None,
            ),
        ]
        url = reverse("evidencias:operacion")

        with patch("evidencias.views.casos_de_cumplimiento", return_value=casos):
            trabajadores = self.client.get(
                f"{url}?estado=sin_evidencia&tipo_centro=farmacia"
                f"&obligacion={obligacion_trabajador.pk}&centro={centro.pk}"
                f"&trabajador={trabajador.pk}&titular=trabajador"
            )
            instalaciones = self.client.get(f"{url}?titular=centro_costo")
            titular_invalido = self.client.get(f"{url}?titular=desconocido")
            identificadores_invalidos = self.client.get(
                f"{url}?tipo_centro=desconocido&centro=abc"
                "&obligacion=abc&trabajador=abc"
            )
            filtros_incompatibles = self.client.get(
                f"{url}?centro={centro.pk}&tipo_centro=bodega"
            )

        self.assertTemplateUsed(trabajadores, "layouts/aplicacion.html")
        self.assertContains(trabajadores, "<main", count=1)
        self.assertContains(trabajadores, "<h1", count=1)
        self.assertContains(trabajadores, "<h1>Operación del piloto</h1>", html=True)
        self.assertContains(trabajadores, "<caption>", count=1)
        self.assertContains(trabajadores, 'scope="col"', count=7)
        self.assertContains(trabajadores, 'name="estado"')
        self.assertContains(trabajadores, 'name="tipo_centro"')
        self.assertContains(trabajadores, 'name="obligacion"')
        self.assertContains(trabajadores, 'name="centro"')
        self.assertContains(trabajadores, 'name="trabajador"')
        self.assertContains(trabajadores, 'name="titular"')
        for valor in (
            "sin_evidencia",
            "farmacia",
            str(obligacion_trabajador.pk),
            str(centro.pk),
            str(trabajador.pk),
            "trabajador",
        ):
            self.assertContains(trabajadores, f'value="{valor}" selected')
        self.assertContains(trabajadores, "••.•••.678-5", count=2)
        self.assertNotContains(trabajadores, "12345678-5")
        self.assertEqual(len(trabajadores.context["casos"]), 1)
        self.assertEqual(trabajadores.context["casos"][0].trabajador, trabajador)
        self.assertEqual(len(instalaciones.context["casos"]), 1)
        self.assertIsNone(instalaciones.context["casos"][0].trabajador)
        self.assertEqual(len(titular_invalido.context["casos"]), 2)
        self.assertEqual(titular_invalido.context["titular_seleccionado"], "")
        self.assertEqual(len(identificadores_invalidos.context["casos"]), 2)
        self.assertEqual(len(filtros_incompatibles.context["casos"]), 0)
        self.assertContains(
            trabajadores,
            reverse("evidencias:cargar", args=[centro.pk, obligacion_trabajador.pk]),
        )
        self.assertNotContains(trabajadores, "<script")

    def test_un_kpi_abre_las_filas_del_titular_que_cuenta(self) -> None:
        centro = CentroCosto.objects.create(
            codigo_contable="FAR-KPI-001",
            nombre="Farmacia de enlace KPI",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        trabajador = crear_trabajador(
            rut="12345678-5",
            nombre="Persona Ficticia de KPI",
            cargo="Cargo ficticio",
            centro=centro,
            motivo="Fixture de enlace KPI",
            actor=self.usuario,
        )
        validar_trabajador(trabajador=trabajador, actor=self.usuario)
        casos = [
            SimpleNamespace(
                centro=centro,
                obligacion=self.obligacion,
                nombre_obligacion="Caso de instalación",
                trabajador=None,
                estado=EstadoCumplimiento.SIN_EVIDENCIA,
                evidencia=None,
                fecha_fin=None,
            ),
            SimpleNamespace(
                centro=centro,
                obligacion=self.obligacion,
                nombre_obligacion="Caso de trabajador",
                trabajador=trabajador,
                estado=EstadoCumplimiento.SIN_EVIDENCIA,
                evidencia=None,
                fecha_fin=None,
            ),
        ]

        with (
            patch("acceso.views.casos_de_cumplimiento", return_value=casos),
            patch("evidencias.views.casos_de_cumplimiento", return_value=casos),
        ):
            portada = self.client.get(reverse("inicio"))
            coincidencia = re.search(
                r'href="([^"]+)" aria-label="1 trabajadores: Sin evidencia"',
                portada.content.decode(),
            )
            if coincidencia is None:
                self.fail("La portada no generó el enlace KPI esperado.")
            destino = self.client.get(unescape(coincidencia.group(1)))

        self.assertEqual(destino.status_code, 200)
        self.assertEqual(len(destino.context["casos"]), 1)
        self.assertEqual(destino.context["casos"][0].trabajador, trabajador)
        self.assertContains(destino, "1 caso titular–obligación")

    def test_conserva_la_proteccion_de_acceso_a_operacion(self) -> None:
        url = reverse("evidencias:operacion")
        self.client.logout()

        anonimo = self.client.get(url)
        usuario_sin_rol = get_user_model().objects.create_user(
            username="sin_rol_operacion",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(usuario_sin_rol)
        prohibido = self.client.get(url)

        self.assertEqual(anonimo.status_code, 302)
        self.assertIn(reverse("iniciar_sesion"), anonimo.headers["Location"])
        self.assertEqual(prohibido.status_code, 403)
