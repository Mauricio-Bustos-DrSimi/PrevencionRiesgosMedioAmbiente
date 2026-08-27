import hashlib
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion


class CargaEvidenciaHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(
            MEDIA_ROOT=self.directorio_temporal.name,
        )
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)
        grupo = Group.objects.get(name="Prevencionista")
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_evidencias",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(grupo)
        self.centro = CentroCosto.objects.create(
            codigo_contable="FAR-EVID-001",
            nombre="Farmacia Evidencia",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        self.obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Mantener extintores certificados",
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
                "motivo": "Aplicación para cargar evidencia",
            },
        )

    def _archivo(self, contenido: bytes = b"certificado de prueba") -> SimpleUploadedFile:
        return SimpleUploadedFile(
            "certificado.pdf",
            contenido,
            content_type="application/pdf",
        )

    def test_prevencionista_carga_evidencia_y_queda_pendiente_con_hash(self) -> None:
        contenido = b"certificado vigente de prueba"
        respuesta = self.client.post(
            reverse(
                "evidencias:cargar",
                args=[self.centro.pk, self.obligacion.pk],
            ),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": "2026-08-01",
                "fecha_vencimiento": "2027-08-01",
                "archivo": self._archivo(contenido),
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Pendiente de validación")
        self.assertContains(respuesta, hashlib.sha256(contenido).hexdigest())
        self.assertContains(respuesta, "Organismo certificador")

    def test_no_se_puede_cargar_evidencia_para_no_aplica(self) -> None:
        self.client.post(
            reverse("planes_aplicacion:no_aplica", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "No corresponde",
            },
        )

        respuesta = self.client.get(
            reverse(
                "evidencias:cargar",
                args=[self.centro.pk, self.obligacion.pk],
            ),
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, "No aplica", status_code=403)

    def test_fallo_de_almacenamiento_no_deja_evidencia_parcial(self) -> None:
        with patch("django.core.files.storage.default_storage.save", side_effect=OSError("disco lleno")):
            respuesta = self.client.post(
                reverse(
                    "evidencias:cargar",
                    args=[self.centro.pk, self.obligacion.pk],
                ),
                {
                    "emisor": "Organismo certificador",
                    "fecha_emision": "2026-08-01",
                    "fecha_vencimiento": "2027-08-01",
                    "archivo": self._archivo(),
                },
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se pudo almacenar la evidencia")
        self.assertNotContains(respuesta, "Pendiente de validación")
