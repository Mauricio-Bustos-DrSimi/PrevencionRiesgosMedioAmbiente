import tempfile
from datetime import date, datetime
from typing import cast
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion

from evidencias.models import Evidencia


@override_settings(DIAS_POR_VENCER=30)
class HistorialCumplimientoHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        grupo = Group.objects.get(name="Prevencionista")
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_historial",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(grupo)
        self.centro = CentroCosto.objects.create(
            codigo_contable="FAR-HIST-001",
            nombre="Farmacia Histórica",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        self.obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Mantener red húmeda operativa",
            norma_origen="DS 594",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.usuario,
            motivo="Alta para reconstrucción histórica",
        )
        self.client.force_login(self.usuario)
        self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "Aplicación inicial histórica",
            },
        )
        self.url_plan = reverse(
            "planes_aplicacion:plan",
            args=[self.centro.pk],
        )

    def _momento(self, ano: int, mes: int, dia: int) -> datetime:
        return datetime(
            ano,
            mes,
            dia,
            10,
            tzinfo=ZoneInfo("America/Santiago"),
        )

    def _consultar(self, fecha: str) -> HttpResponse:
        return cast(HttpResponse, self.client.get(f"{self.url_plan}?fecha={fecha}"))

    def _cargar(
        self,
        *,
        momento: datetime,
        fecha_emision: str,
        fecha_vencimiento: str,
        emisor: str,
    ) -> Evidencia:
        with patch("django.utils.timezone.now", return_value=momento), patch(
            "django.utils.timezone.localdate",
            return_value=momento.date(),
        ):
            self.client.force_login(self.usuario)
            self.client.post(
                reverse(
                    "evidencias:cargar",
                    args=[self.centro.pk, self.obligacion.pk],
                ),
                {
                    "emisor": emisor,
                    "fecha_emision": fecha_emision,
                    "fecha_vencimiento": fecha_vencimiento,
                    "archivo": SimpleUploadedFile(
                        "evidencia.pdf",
                        emisor.encode(),
                        content_type="application/pdf",
                    ),
                },
            )
        evidencia = Evidencia.objects.filter(
            centro_costo=self.centro,
            obligacion=self.obligacion,
        ).first()
        assert evidencia is not None
        return evidencia

    def _validar(self, evidencia: Evidencia, *, momento: datetime) -> None:
        with patch("django.utils.timezone.now", return_value=momento), patch(
            "django.utils.timezone.localdate",
            return_value=momento.date(),
        ):
            self.client.force_login(self.usuario)
            self.client.post(reverse("evidencias:validar", args=[evidencia.pk]))

    def test_reconstruye_ciclo_completo_sin_modificar_la_historia(self) -> None:
        sin_evidencia = self._consultar("2026-08-28")

        anterior = self._cargar(
            momento=self._momento(2026, 9, 1),
            fecha_emision="2026-08-20",
            fecha_vencimiento="2026-10-31",
            emisor="Certificador inicial",
        )
        pendiente_inicial = self._consultar("2026-09-01")
        self._validar(anterior, momento=self._momento(2026, 9, 2))
        vigente = self._consultar("2026-09-15")
        por_vencer = self._consultar("2026-10-15")
        vencido = self._consultar("2026-11-01")

        renovada = self._cargar(
            momento=self._momento(2026, 11, 2),
            fecha_emision="2026-11-02",
            fecha_vencimiento="2027-11-02",
            emisor="Certificador renovación",
        )
        pendiente_renovacion = self._consultar("2026-11-02")
        self._validar(renovada, momento=self._momento(2026, 11, 3))
        vigente_renovado = self._consultar("2026-11-03")

        with patch(
            "django.utils.timezone.now",
            return_value=self._momento(2026, 11, 4),
        ):
            self.client.force_login(self.usuario)
            self.client.post(
                reverse("planes_aplicacion:no_aplica", args=[self.centro.pk]),
                {
                    "obligacion": str(self.obligacion.pk),
                    "motivo": "Cambio de aplicabilidad histórico",
                },
            )
        no_aplica = self._consultar("2026-11-04")

        self.assertContains(sin_evidencia, "Sin evidencia")
        self.assertContains(pendiente_inicial, "Pendiente de validación")
        self.assertContains(vigente, "Vigente")
        self.assertContains(por_vencer, "Por vencer")
        self.assertContains(vencido, "Vencido")
        self.assertContains(
            vencido,
            reverse("evidencias:validar", args=[anterior.pk]),
        )
        self.assertContains(pendiente_renovacion, "Pendiente de validación")
        self.assertContains(vigente_renovado, "Vigente")
        self.assertContains(
            vigente_renovado,
            reverse("evidencias:validar", args=[renovada.pk]),
        )
        self.assertContains(no_aplica, "No aplica")
        self.assertNotContains(
            no_aplica,
            reverse("evidencias:validar", args=[renovada.pk]),
        )

    def test_muestra_la_version_de_obligacion_que_existia_en_la_fecha(self) -> None:
        with patch(
            "django.utils.timezone.now",
            return_value=self._momento(2026, 10, 1),
        ):
            self.client.force_login(self.usuario)
            self.client.post(
                reverse("obligaciones:corregir", args=[self.obligacion.pk]),
                {
                    "nombre": "Mantener red húmeda certificada",
                    "norma_origen": "DS 594 actualizado",
                    "titular": "centro_costo",
                    "periodicidad": "anual",
                    "motivo": "Cambio normativo con vigencia histórica",
                },
            )

        antes = self._consultar("2026-09-30")
        despues = self._consultar("2026-10-01")

        self.assertContains(antes, "Mantener red húmeda operativa")
        self.assertNotContains(antes, "Mantener red húmeda certificada")
        self.assertContains(despues, "Mantener red húmeda certificada")
        self.assertNotContains(despues, "Mantener red húmeda operativa")

    def test_fecha_historica_invalida_recibe_una_respuesta_clara(self) -> None:
        respuesta = self.client.get(f"{self.url_plan}?fecha=no-es-una-fecha")

        self.assertEqual(respuesta.status_code, 400)
        self.assertContains(
            respuesta,
            "La fecha histórica debe usar el formato AAAA-MM-DD",
            status_code=400,
        )

    def test_plan_permite_seleccionar_la_fecha_historica(self) -> None:
        respuesta = self.client.get(self.url_plan)

        self.assertContains(respuesta, 'name="fecha"')
        self.assertContains(respuesta, 'type="date"')
        self.assertContains(respuesta, "Consultar estado pasado")
