import hashlib
import tempfile
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion

from evidencias.models import Evidencia


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

    def _cargar_evidencia(
        self,
        *,
        fecha_emision: str = "2026-08-01",
        fecha_vencimiento: str = "2027-08-01",
    ) -> Evidencia:
        respuesta = self.client.post(
            reverse(
                "evidencias:cargar",
                args=[self.centro.pk, self.obligacion.pk],
            ),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": fecha_emision,
                "fecha_vencimiento": fecha_vencimiento,
                "archivo": self._archivo(),
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        return Evidencia.objects.get()

    def test_bandeja_abre_evidencia_pendiente_con_contexto(self) -> None:
        evidencia = self._cargar_evidencia()

        bandeja = self.client.get(reverse("evidencias:pendientes"))

        self.assertEqual(bandeja.status_code, 200)
        self.assertContains(bandeja, "Farmacia Evidencia")
        self.assertContains(bandeja, "Mantener extintores certificados")
        self.assertContains(bandeja, "Pendiente de validación")
        self.assertContains(
            bandeja,
            reverse("evidencias:validar", args=[evidencia.pk]),
        )

        detalle = self.client.get(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )

        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, "Farmacia Evidencia")
        self.assertContains(detalle, "Mantener extintores certificados")
        self.assertContains(detalle, "Organismo certificador")
        self.assertContains(detalle, "Pendiente de validación")
        self.assertContains(detalle, "No cumplida")
        self.assertContains(detalle, "Validar evidencia")

    def test_validacion_deriva_vigente_y_registra_identidad_y_bitacora(self) -> None:
        evidencia = self._cargar_evidencia()
        momento_validacion = datetime(
            2026,
            8,
            27,
            12,
            tzinfo=ZoneInfo("America/Santiago"),
        )

        pendiente = self.client.get(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(pendiente, "Pendiente de validación")
        self.assertContains(pendiente, "No cumplida")

        with patch(
            "django.utils.timezone.localdate",
            return_value=date(2026, 8, 27),
        ), patch(
            "django.utils.timezone.now",
            return_value=momento_validacion,
        ):
            respuesta = self.client.post(
                reverse("evidencias:validar", args=[evidencia.pk]),
                follow=True,
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Vigente")
        self.assertContains(respuesta, "Anual")
        self.assertContains(respuesta, "prevencionista_evidencias")
        self.assertContains(respuesta, "27 de agosto de 2026")
        self.assertNotContains(respuesta, 'name="estado"')
        self.assertNotContains(
            self.client.get(reverse("evidencias:pendientes")),
            "Farmacia Evidencia",
        )

        sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_evidencias",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)
        bitacora = self.client.get("/admin/bitacora/eventobitacora/")

        self.assertContains(bitacora, "prevencionista_evidencias")
        self.assertContains(bitacora, "validar_evidencia")
        self.assertContains(bitacora, str(evidencia.pk))
        self.assertEqual(
            self.client.get("/admin/evidencias/evidencia/").status_code,
            404,
        )

    def test_sysadmin_sin_rol_prevencionista_no_puede_validar(self) -> None:
        evidencia = self._cargar_evidencia()
        sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_sin_rol_prevencionista",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)

        respuesta = self.client.post(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_periodicidad_anual_limita_la_vigencia_a_un_ano(self) -> None:
        evidencia = self._cargar_evidencia(
            fecha_emision="2026-08-01",
            fecha_vencimiento="2030-08-01",
        )
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=2,
            nombre="Mantener extintores sin renovación periódica",
            norma_origen="DS 594 corregido",
            titular="centro_costo",
            periodicidad="permanente",
            tipo_version=TipoVersion.CORRECCION,
            autor=self.usuario,
            motivo="Cambio posterior a la carga",
        )
        with patch(
            "django.utils.timezone.localdate",
            return_value=date(2027, 8, 2),
        ):
            respuesta = self.client.post(
                reverse("evidencias:validar", args=[evidencia.pk]),
                follow=True,
            )

        self.assertNotContains(respuesta, "Vigente")
        self.assertContains(respuesta, "Validada sin vigencia actual")

    def test_usuario_sin_rol_no_puede_validar_evidencia(self) -> None:
        evidencia = self._cargar_evidencia()
        usuario_sin_rol = get_user_model().objects.create_user(
            username="sin_rol_evidencias",
        )
        self.client.force_login(usuario_sin_rol)

        respuesta = self.client.post(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )

        self.assertEqual(respuesta.status_code, 403)
        self.client.force_login(self.usuario)
        detalle = self.client.get(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(detalle, "Pendiente de validación")
        self.assertContains(detalle, "No cumplida")

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
