import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from bitacora.models import EventoBitacora
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion


CONTENIDO = b"evidencia ficticia para verificar integridad"


class IntegridadEvidenciaHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_integridad",
            password="clave-segura-de-prueba",
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))
        self.usuario_sin_permiso = get_user_model().objects.create_user(
            username="sin_permiso_integridad",
            password="clave-segura-de-prueba",
        )
        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM-INTEGRIDAD",
            nombre="Centro ficticio de integridad",
            tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
        )
        self.obligacion = Obligacion.objects.create()
        self.version = VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Obligacion ficticia de integridad",
            norma_origen="Fuente ficticia",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta para prueba de integridad",
        )
        self.evidencia = Evidencia.objects.create(
            centro_costo=self.centro,
            obligacion=self.obligacion,
            version_obligacion=self.version,
            archivo=SimpleUploadedFile(
                "evidencia-ficticia.pdf",
                CONTENIDO,
                content_type="application/pdf",
            ),
            hash_sha256=hashlib.sha256(CONTENIDO).hexdigest(),
            emisor="Emisor ficticio",
            fecha_emision="2026-01-01",
            fecha_vencimiento="2027-01-01",
            cargada_por=self.prevencionista,
        )
        self.url = reverse(
            "evidencias:verificar_integridad",
            args=[self.evidencia.pk],
        )

    def test_get_solo_confirma_sin_calcular_hash_ni_registrar_evento(self) -> None:
        self.client.force_login(self.prevencionista)

        with patch("evidencias.views.verificar_integridad_archivo") as verificar:
            respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Confirmar verificación de integridad")
        self.assertContains(respuesta, 'method="post"')
        self.assertContains(respuesta, "csrfmiddlewaretoken")
        verificar.assert_not_called()
        self.assertFalse(
            EventoBitacora.objects.filter(accion="verificar_integridad").exists()
        )

    def test_post_autorizado_verifica_sin_modificar_archivo_ni_hash(self) -> None:
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.prevencionista)
        cliente.get(self.url)
        token_csrf = cliente.cookies["csrftoken"].value
        ruta = Path(self.evidencia.archivo.path)
        bytes_antes = ruta.read_bytes()
        hash_antes = self.evidencia.hash_sha256

        respuesta = cliente.post(
            self.url,
            {"csrfmiddlewaretoken": token_csrf},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Coincide")
        self.assertContains(respuesta, hash_antes, count=2)
        evento = EventoBitacora.objects.get(accion="verificar_integridad")
        self.assertEqual(evento.actor, self.prevencionista)
        self.assertEqual(evento.evidencia, self.evidencia)
        self.evidencia.refresh_from_db()
        self.assertEqual(self.evidencia.hash_sha256, hash_antes)
        self.assertEqual(ruta.read_bytes(), bytes_antes)

    def test_cada_post_valido_registra_exactamente_un_evento(self) -> None:
        self.client.force_login(self.prevencionista)

        self.client.post(self.url)
        self.client.post(self.url)

        self.assertEqual(
            EventoBitacora.objects.filter(
                accion="verificar_integridad",
                actor=self.prevencionista,
                evidencia=self.evidencia,
            ).count(),
            2,
        )

    def test_post_sin_csrf_es_rechazado_sin_abrir_archivo_ni_crear_evento(self) -> None:
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.prevencionista)

        with patch.object(self.evidencia.archivo.storage, "open") as abrir:
            respuesta = cliente.post(self.url)

        self.assertEqual(respuesta.status_code, 403)
        abrir.assert_not_called()
        self.assertFalse(
            EventoBitacora.objects.filter(accion="verificar_integridad").exists()
        )

    def test_post_sin_permiso_es_rechazado_antes_de_abrir_el_archivo(self) -> None:
        self.client.force_login(self.usuario_sin_permiso)

        with patch.object(self.evidencia.archivo.storage, "open") as abrir:
            respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 403)
        abrir.assert_not_called()
        self.assertFalse(
            EventoBitacora.objects.filter(accion="verificar_integridad").exists()
        )

    def test_metodo_distinto_de_get_y_post_es_rechazado_sin_abrir_archivo(self) -> None:
        self.client.force_login(self.prevencionista)

        with patch.object(self.evidencia.archivo.storage, "open") as abrir:
            respuesta = self.client.put(self.url)

        self.assertEqual(respuesta.status_code, 405)
        abrir.assert_not_called()
        self.assertFalse(
            EventoBitacora.objects.filter(accion="verificar_integridad").exists()
        )

    def test_archivo_alterado_se_detecta_sin_reemplazar_hash_registrado(self) -> None:
        self.client.force_login(self.prevencionista)
        hash_registrado = self.evidencia.hash_sha256
        Path(self.evidencia.archivo.path).write_bytes(b"contenido alterado")

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No coincide")
        self.assertContains(respuesta, "Alteración detectada")
        self.evidencia.refresh_from_db()
        self.assertEqual(self.evidencia.hash_sha256, hash_registrado)
