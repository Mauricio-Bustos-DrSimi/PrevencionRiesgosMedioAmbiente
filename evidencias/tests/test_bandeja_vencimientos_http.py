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
                "fecha_emision": "2026-01-01",
                "fecha_vencimiento": fecha_vencimiento,
                "archivo": SimpleUploadedFile(
                    "certificado.pdf",
                    b"certificado para transiciones",
                    content_type="application/pdf",
                ),
            },
        )
        evidencia = Evidencia.objects.get(
            centro_costo=centro,
            obligacion=obligacion,
        )
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
        self._cargar_y_validar()
        obligacion_por_vencer = self._crear_obligacion("Realizar inspección anual")
        self._cargar_y_validar(
            obligacion_por_vencer,
            fecha_vencimiento="2027-01-20",
        )
        self._crear_obligacion("Mantener señalética instalada")
        url = reverse("evidencias:vencimientos")

        with patch("evidencias.views.timezone.localdate", return_value=date(2027, 1, 1)):
            vencidas = self.client.get(f"{url}?estado=vencido")
            por_vencer = self.client.get(f"{url}?estado=por_vencer")
            sin_evidencia = self.client.get(f"{url}?estado=sin_evidencia")

        self.assertContains(
            vencidas,
            "Farmacia Vencimientos — Mantener extintores vigentes",
        )
        self.assertNotContains(
            vencidas,
            "Farmacia Vencimientos — Realizar inspección anual",
        )
        self.assertNotContains(
            vencidas,
            "Farmacia Vencimientos — Mantener señalética instalada",
        )

        self.assertContains(
            por_vencer,
            "Farmacia Vencimientos — Realizar inspección anual",
        )
        self.assertNotContains(
            por_vencer,
            "Farmacia Vencimientos — Mantener extintores vigentes",
        )
        self.assertNotContains(
            por_vencer,
            "Farmacia Vencimientos — Mantener señalética instalada",
        )

        self.assertContains(
            sin_evidencia,
            "Farmacia Vencimientos — Mantener señalética instalada",
        )
        self.assertContains(sin_evidencia, "Sin evidencia")
        self.assertNotContains(
            sin_evidencia,
            "Farmacia Vencimientos — Mantener extintores vigentes",
        )

    def test_filtra_por_tipo_de_centro_y_obligacion(self) -> None:
        self._cargar_y_validar()
        otra_obligacion = self._crear_obligacion("Revisar vías de evacuación")
        self._cargar_y_validar(otra_obligacion)
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
        self._cargar_y_validar(self.obligacion, centro=bodega)
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

        self.assertContains(por_obligacion, "Revisar vías de evacuación")
        self.assertNotContains(
            por_obligacion,
            "Farmacia Vencimientos — Mantener extintores vigentes",
        )
