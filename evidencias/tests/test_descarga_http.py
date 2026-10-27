import hashlib
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import cast
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse, HttpResponse
from django.test import TestCase
from django.urls import reverse

from bitacora.models import EventoBitacora
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import (
    ClasificacionEvidencia,
    Obligacion,
    TipoVersion,
    VersionObligacion,
)
from trabajadores.models import AsignacionTrabajador, TipoAsignacion, Trabajador


CLAVE_PRUEBA = "clave-segura-de-prueba"
CONTENIDO = b"examen ocupacional ficticio"


class DescargaEvidenciaHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_descarga",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))
        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_descarga",
            password=CLAVE_PRUEBA,
        )
        self.usuario_sin_permiso = get_user_model().objects.create_user(
            username="sin_permiso_descarga",
            password=CLAVE_PRUEBA,
        )
        self.encargado = get_user_model().objects.create_user(
            username="encargado_descarga",
            password=CLAVE_PRUEBA,
        )
        self.encargado.groups.add(Group.objects.get(name="Encargado"))
        self.lector = get_user_model().objects.create_user(
            username="lector_descarga",
            password=CLAVE_PRUEBA,
        )
        self.lector.groups.add(Group.objects.create(name="Lector"))
        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM-DESCARGA",
            nombre="Centro de prueba de descarga",
            tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
        )
        self.obligacion = Obligacion.objects.create()
        self.version = VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Examen ocupacional de prueba",
            norma_origen="Fuente ficticia de prueba",
            titular="trabajador",
            periodicidad="por_evento",
            clasificacion_evidencia=ClasificacionEvidencia.SALUD_OCUPACIONAL,
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta ficticia para probar la descarga",
        )
        self.trabajador = Trabajador.objects.create(
            rut="12345678-5",
            nombre="Persona ficticia",
            cargo="Cargo ficticio",
            creado_por=self.prevencionista,
        )
        AsignacionTrabajador.objects.create(
            trabajador=self.trabajador,
            centro_costo=self.centro,
            tipo=TipoAsignacion.ALTA,
            motivo="Asignación ficticia para probar la descarga",
            autor=self.prevencionista,
        )
        self.evidencia = Evidencia.objects.create(
            centro_costo=self.centro,
            obligacion=self.obligacion,
            version_obligacion=self.version,
            trabajador=self.trabajador,
            archivo=SimpleUploadedFile(
                "examen-ocupacional-persona-12345678-9.pdf",
                CONTENIDO,
                content_type="application/pdf",
            ),
            hash_sha256=hashlib.sha256(CONTENIDO).hexdigest(),
            emisor="Prestador ficticio",
            fecha_emision="2026-01-01",
            fecha_vencimiento="2027-01-01",
            cargada_por=self.prevencionista,
        )
        self.url = reverse("evidencias:descargar", args=[self.evidencia.pk])

    def test_usuario_anonimo_es_redirigido_sin_abrir_el_archivo(self) -> None:
        with patch.object(self.evidencia.archivo.storage, "open") as abrir:
            respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)
        abrir.assert_not_called()
        self.assertIn(reverse("iniciar_sesion"), respuesta.headers["Location"])
        self.assertFalse(
            EventoBitacora.objects.filter(
                accion="descargar_evidencia",
                evidencia=self.evidencia,
            ).exists()
        )

    def test_roles_sin_permiso_reciben_403_sin_abrir_el_archivo(self) -> None:
        for usuario in (self.usuario_sin_permiso, self.encargado, self.lector):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                with patch.object(self.evidencia.archivo.storage, "open") as abrir:
                    respuesta = self.client.get(self.url)

                self.assertEqual(respuesta.status_code, 403)
                abrir.assert_not_called()
        self.assertFalse(
            EventoBitacora.objects.filter(
                accion="descargar_evidencia",
                evidencia=self.evidencia,
            ).exists()
        )

    def test_operadores_actuales_descargan_bytes_intactos_y_quedan_en_bitacora(
        self,
    ) -> None:
        hash_antes = self.evidencia.hash_sha256
        ruta = Path(self.evidencia.archivo.path)
        bytes_antes = ruta.read_bytes()

        for usuario in (self.prevencionista, self.sysadmin):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = cast(FileResponse, self.client.get(self.url))

                self.assertEqual(respuesta.status_code, 200)
                contenido = b"".join(
                    cast(Iterable[bytes], respuesta.streaming_content)
                )
                self.assertEqual(contenido, CONTENIDO)
                self.assertEqual(
                    respuesta.headers["Content-Type"],
                    "application/octet-stream",
                )
                self.assertEqual(
                    respuesta.headers["X-Content-Type-Options"],
                    "nosniff",
                )
                disposicion = respuesta.headers["Content-Disposition"]
                self.assertIn("attachment", disposicion)
                self.assertIn(f"evidencia-{self.evidencia.pk}.pdf", disposicion)
                self.assertNotIn("12345678-9", disposicion)
                self.assertNotIn(self.directorio_temporal.name, str(respuesta.headers))
                self.assertTrue(
                    EventoBitacora.objects.filter(
                        accion="descargar_evidencia",
                        evidencia=self.evidencia,
                        actor=usuario,
                    ).exists()
                )

        self.evidencia.refresh_from_db()
        self.assertEqual(self.evidencia.hash_sha256, hash_antes)
        self.assertEqual(ruta.read_bytes(), bytes_antes)

    def test_identificador_inexistente_responde_404_sin_registrar_evento(self) -> None:
        self.client.force_login(self.prevencionista)

        respuesta = self.client.get(
            reverse("evidencias:descargar", args=[self.evidencia.pk + 999]),
        )

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(
            EventoBitacora.objects.filter(accion="descargar_evidencia").exists()
        )

    def test_detalle_y_recorrido_enlazan_la_descarga_protegida(self) -> None:
        self.client.force_login(self.prevencionista)

        detalle = cast(
            HttpResponse,
            self.client.get(
                reverse("evidencias:validar", args=[self.evidencia.pk]),
            ),
        )
        recorrido = cast(
            HttpResponse,
            self.client.get(
                reverse(
                    "bitacora:recorrido",
                    args=[self.centro.pk, self.obligacion.pk],
                ),
            ),
        )

        for respuesta in (detalle, recorrido):
            self.assertContains(respuesta, self.url)
            self.assertNotContains(respuesta, self.evidencia.archivo.url)
