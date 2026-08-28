import tempfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion

from evidencias.models import Evidencia


class RenovacionEvidenciaHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        grupo = Group.objects.get(name="Prevencionista")
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_renovacion",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(grupo)
        self.centro = CentroCosto.objects.create(
            codigo_contable="FAR-REN-001",
            nombre="Farmacia Renovación",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        self.obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Mantener sistema contra incendios",
            norma_origen="DS 594",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.usuario,
            motivo="Alta para ciclo de renovación",
        )
        self.client.force_login(self.usuario)
        self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "Aplicación para ciclo de renovación",
            },
        )

    def _cargar(
        self,
        *,
        emisor: str,
        fecha_emision: str,
        fecha_vencimiento: str,
        contenido: bytes,
    ) -> Evidencia:
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
                    contenido,
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

    def test_renueva_una_obligacion_vencida_y_conserva_la_evidencia_anterior(
        self,
    ) -> None:
        anterior = self._cargar(
            emisor="Certificador inicial",
            fecha_emision="2025-01-01",
            fecha_vencimiento="2025-12-31",
            contenido=b"evidencia inicial",
        )
        self.client.post(reverse("evidencias:validar", args=[anterior.pk]))

        with patch(
            "evidencias.views.timezone.localdate",
            return_value=date(2026, 1, 15),
        ):
            detalle_vencido = self.client.get(
                reverse("evidencias:validar", args=[anterior.pk])
            )

        self.assertContains(detalle_vencido, "Vencido")
        self.assertContains(
            detalle_vencido,
            reverse(
                "evidencias:cargar",
                args=[self.centro.pk, self.obligacion.pk],
            ),
        )

        renovada = self._cargar(
            emisor="Certificador renovación",
            fecha_emision="2026-01-10",
            fecha_vencimiento="2027-01-10",
            contenido=b"evidencia renovada",
        )
        with patch(
            "evidencias.views.timezone.localdate",
            return_value=date(2026, 1, 15),
        ):
            self.client.post(reverse("evidencias:validar", args=[renovada.pk]))
            detalle_renovado = self.client.get(
                reverse("evidencias:validar", args=[renovada.pk])
            )

        self.assertContains(detalle_renovado, "Vigente")
        self.assertContains(detalle_renovado, "Certificador inicial")
        self.assertContains(detalle_renovado, "Certificador renovación")
        self.assertContains(
            detalle_renovado,
            reverse("evidencias:validar", args=[anterior.pk]),
        )
        self.assertContains(
            detalle_renovado,
            reverse("evidencias:validar", args=[renovada.pk]),
        )

        detalle_anterior = self.client.get(
            reverse("evidencias:validar", args=[anterior.pk])
        )
        self.assertContains(detalle_anterior, "Certificador inicial")
