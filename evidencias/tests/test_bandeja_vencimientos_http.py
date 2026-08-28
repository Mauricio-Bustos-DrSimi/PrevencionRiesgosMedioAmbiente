import tempfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion

from evidencias.models import Evidencia


@override_settings(DIAS_POR_VENCER=30)
class BandejaVencimientosHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        grupo = Group.objects.get(name="Prevencionista")
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_vencimientos",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(grupo)
        self.centro = CentroCosto.objects.create(
            codigo_contable="FAR-VENC-001",
            nombre="Farmacia Vencimientos",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
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
            motivo="Alta de prueba",
        )
        self.client.force_login(self.usuario)
        self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "Aplicación para probar vencimientos",
            },
        )

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
            motivo="Alta de prueba",
        )
        self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {
                "obligacion": str(obligacion.pk),
                "motivo": "Aplicación para probar vencimientos",
            },
        )
        return obligacion

    def _cargar_y_validar(
        self,
        obligacion: Obligacion | None = None,
        *,
        centro: CentroCosto | None = None,
        fecha_emision: str = "2026-01-01",
        fecha_vencimiento: str = "2026-12-31",
    ) -> Evidencia:
        obligacion = obligacion or self.obligacion
        centro = centro or self.centro
        self.client.post(
            reverse(
                "evidencias:cargar",
                args=[centro.pk, obligacion.pk],
            ),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": fecha_emision,
                "fecha_vencimiento": fecha_vencimiento,
                "archivo": SimpleUploadedFile(
                    "certificado.pdf",
                    b"certificado para transiciones",
                    content_type="application/pdf",
                ),
            },
        )
        evidencia = Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
        ).first()
        assert evidencia is not None
        self.client.post(reverse("evidencias:validar", args=[evidencia.pk]))
        return evidencia

    def test_estado_cambia_con_el_tiempo_y_el_umbral_configurado(self) -> None:
        evidencia = self._cargar_y_validar()
        url = reverse("evidencias:vencimientos")

        with patch("evidencias.views.timezone.localdate", return_value=date(2026, 11, 30)):
            vigente = self.client.get(url)

        self.assertContains(vigente, "Umbral de Por vencer: 30 días")
        self.assertNotContains(vigente, "Farmacia Vencimientos")

        with patch("evidencias.views.timezone.localdate", return_value=date(2026, 12, 1)):
            por_vencer = self.client.get(url)
            detalle_por_vencer = self.client.get(
                reverse("evidencias:validar", args=[evidencia.pk])
            )

        self.assertContains(por_vencer, "Farmacia Vencimientos")
        self.assertContains(por_vencer, "Por vencer")
        self.assertContains(
            por_vencer,
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(
            por_vencer,
            reverse("centros_costo:detalle", args=[self.centro.pk]),
        )
        self.assertContains(
            por_vencer,
            reverse("obligaciones:detalle", args=[self.obligacion.pk]),
        )
        self.assertContains(detalle_por_vencer, "Por vencer")

        with patch("evidencias.views.timezone.localdate", return_value=date(2027, 1, 1)):
            vencido = self.client.get(url)
            detalle_vencido = self.client.get(
                reverse("evidencias:validar", args=[evidencia.pk])
            )

        self.assertContains(vencido, "Farmacia Vencimientos")
        self.assertContains(vencido, "— Vencido —")
        self.assertNotContains(vencido, "— Por vencer —")
        self.assertContains(detalle_vencido, "Vencido")
        self.assertNotContains(detalle_vencido, "Fuera de la ventana calculada")

    def test_filtro_distingue_vencido_por_vencer_y_sin_evidencia(self) -> None:
        evidencia_vencida = self._cargar_y_validar()
        obligacion_por_vencer = self._crear_obligacion("Realizar inspección anual")
        evidencia_por_vencer = self._cargar_y_validar(
            obligacion_por_vencer,
            fecha_vencimiento="2027-01-20",
        )
        obligacion_sin_evidencia = self._crear_obligacion(
            "Mantener señalética instalada"
        )
        url = reverse("evidencias:vencimientos")
        url_vencida = reverse("evidencias:validar", args=[evidencia_vencida.pk])
        url_por_vencer = reverse(
            "evidencias:validar",
            args=[evidencia_por_vencer.pk],
        )
        url_sin_evidencia = reverse(
            "evidencias:cargar",
            args=[self.centro.pk, obligacion_sin_evidencia.pk],
        )

        with patch("evidencias.views.timezone.localdate", return_value=date(2027, 1, 1)):
            vencidas = self.client.get(f"{url}?estado=vencido")
            por_vencer = self.client.get(f"{url}?estado=por_vencer")
            sin_evidencia = self.client.get(f"{url}?estado=sin_evidencia")

        self.assertContains(vencidas, url_vencida)
        self.assertNotContains(vencidas, url_por_vencer)
        self.assertNotContains(vencidas, url_sin_evidencia)

        self.assertContains(por_vencer, url_por_vencer)
        self.assertNotContains(por_vencer, url_vencida)
        self.assertNotContains(por_vencer, url_sin_evidencia)

        self.assertContains(sin_evidencia, url_sin_evidencia)
        self.assertContains(sin_evidencia, "Sin evidencia")
        self.assertNotContains(sin_evidencia, url_vencida)

    def test_filtra_por_tipo_de_centro_y_obligacion(self) -> None:
        evidencia_farmacia = self._cargar_y_validar()
        otra_obligacion = self._crear_obligacion("Revisar vías de evacuación")
        evidencia_otra_obligacion = self._cargar_y_validar(otra_obligacion)
        bodega = CentroCosto.objects.create(
            codigo_contable="BOD-VENC-001",
            nombre="Bodega Vencimientos",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.client.post(
            reverse("planes_aplicacion:agregar", args=[bodega.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "Aplicación en bodega",
            },
        )
        evidencia_bodega = self._cargar_y_validar(self.obligacion, centro=bodega)
        url = reverse("evidencias:vencimientos")

        with patch("evidencias.views.timezone.localdate", return_value=date(2027, 1, 1)):
            farmacias = self.client.get(
                f"{url}?estado=vencido&tipo_centro=farmacia"
            )
            por_obligacion = self.client.get(
                f"{url}?estado=vencido&obligacion={otra_obligacion.pk}"
            )

        self.assertContains(farmacias, "Farmacia Vencimientos")
        self.assertNotContains(farmacias, "Bodega Vencimientos")
        self.assertNotContains(
            farmacias,
            reverse("evidencias:validar", args=[evidencia_bodega.pk]),
        )

        self.assertContains(
            por_obligacion,
            reverse("evidencias:validar", args=[evidencia_otra_obligacion.pk]),
        )
        self.assertNotContains(
            por_obligacion,
            reverse("evidencias:validar", args=[evidencia_farmacia.pk]),
        )
        self.assertNotContains(
            por_obligacion,
            reverse("evidencias:validar", args=[evidencia_bodega.pk]),
        )

    def test_evidencia_futura_no_oculta_la_vigencia_actual(self) -> None:
        evidencia_actual = self._cargar_y_validar(
            fecha_vencimiento="2026-09-10",
        )
        evidencia_futura = self._cargar_y_validar(
            fecha_emision="2027-01-01",
            fecha_vencimiento="2027-12-31",
        )
        url = reverse("evidencias:vencimientos")

        with patch("evidencias.views.timezone.localdate", return_value=date(2026, 8, 28)):
            bandeja = self.client.get(f"{url}?estado=por_vencer")
            detalle_futuro = self.client.get(
                reverse("evidencias:validar", args=[evidencia_futura.pk])
            )

        self.assertContains(bandeja, "— Por vencer —")
        self.assertContains(
            bandeja,
            reverse("evidencias:validar", args=[evidencia_actual.pk]),
        )
        self.assertNotContains(
            bandeja,
            reverse("evidencias:validar", args=[evidencia_futura.pk]),
        )
        self.assertContains(detalle_futuro, "Sin evidencia")
        self.assertNotContains(detalle_futuro, ">Vigente<")
