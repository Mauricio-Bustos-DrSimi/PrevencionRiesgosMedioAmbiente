import tempfile
from pathlib import Path
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from bitacora.models import EventoBitacora
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import Obligacion
from planes_aplicacion.models import CambioAplicabilidad


CLAVE_PRUEBA = "clave-segura-de-prueba"


class TrazabilidadHttpTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_trazabilidad",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_trazabilidad",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))

    def _crear_recorrido(self) -> tuple[CentroCosto, Obligacion, Evidencia]:
        self.client.force_login(self.sysadmin)
        alta_centro = self.client.post(
            reverse("admin:centros_costo_centrocosto_add"),
            {
                "codigo_contable": "FAR-TRAZ-001",
                "nombre": "Farmacia Trazabilidad",
                "tipo": "farmacia",
                "cve_unidad": "CL-901",
                "_save": "Guardar",
            },
        )
        self.assertEqual(alta_centro.status_code, 302)
        centro = CentroCosto.objects.get(codigo_contable="FAR-TRAZ-001")

        self.client.force_login(self.prevencionista)
        alta_obligacion = self.client.post(
            reverse("obligaciones:crear"),
            {
                "nombre": "Mantener extintores certificados",
                "norma_origen": "DS 594, artículo 45",
                "titular": "centro_costo",
                "periodicidad": "anual",
                "motivo": "Alta del recorrido fiscalizable",
            },
        )
        self.assertEqual(alta_obligacion.status_code, 302)
        obligacion = Obligacion.objects.get()

        aplicacion = self.client.post(
            reverse("planes_aplicacion:agregar", args=[centro.pk]),
            {
                "obligacion": str(obligacion.pk),
                "motivo": "Aplica al centro fiscalizado",
            },
        )
        self.assertEqual(aplicacion.status_code, 302)
        carga = self.client.post(
            reverse("evidencias:cargar", args=[centro.pk, obligacion.pk]),
            {
                "emisor": "Organismo certificador",
                "fecha_emision": "2026-08-01",
                "fecha_vencimiento": "2027-08-01",
                "archivo": SimpleUploadedFile(
                    "certificado.pdf",
                    b"contenido fiscalizable",
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(carga.status_code, 200)
        evidencia = Evidencia.objects.get()
        validacion = self.client.post(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertEqual(validacion.status_code, 302)

        correccion = self.client.post(
            reverse("obligaciones:corregir", args=[obligacion.pk]),
            {
                "nombre": "Mantener extintores con certificación vigente",
                "norma_origen": "DS 594, artículos 45 y 48",
                "titular": "centro_costo",
                "periodicidad": "anual",
                "motivo": "Corrección normativa trazable",
            },
        )
        self.assertEqual(correccion.status_code, 302)

        self.client.force_login(self.sysadmin)
        cambio_centro = self.client.post(
            reverse("admin:centros_costo_centrocosto_change", args=[centro.pk]),
            {
                "codigo_contable": centro.codigo_contable,
                "nombre": "Farmacia Trazabilidad Centro",
                "tipo": "farmacia",
                "cve_unidad": "CL-901",
                "_save": "Guardar",
            },
        )
        self.assertEqual(cambio_centro.status_code, 302)
        centro.refresh_from_db()

        cambio_plan_admin = self.client.post(
            reverse("admin:planes_aplicacion_cambioaplicabilidad_add"),
            {
                "centro_costo": str(centro.pk),
                "obligacion": str(obligacion.pk),
                "aplica": "on",
                "motivo": "Confirmación equivalente desde el panel administrativo",
                "_save": "Guardar",
            },
        )
        self.assertEqual(cambio_plan_admin.status_code, 302)
        return centro, obligacion, evidencia

    def test_fiscalizador_consulta_el_recorrido_completo_de_ambos_canales(
        self,
    ) -> None:
        centro, obligacion, evidencia = self._crear_recorrido()
        self.client.force_login(self.prevencionista)

        respuesta = cast(
            HttpResponse,
            self.client.get(
                reverse(
                    "bitacora:recorrido",
                    args=[centro.pk, obligacion.pk],
                ),
            ),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Recorrido de trazabilidad")
        self.assertContains(respuesta, "Farmacia Trazabilidad Centro")
        self.assertContains(respuesta, "Mantener extintores certificados")
        self.assertContains(respuesta, "Mantener extintores con certificación vigente")
        self.assertContains(respuesta, "Qué ocurrió")
        self.assertContains(respuesta, "Quién actuó")
        self.assertContains(respuesta, "Cómo")
        self.assertContains(respuesta, "Cuándo")
        self.assertContains(respuesta, "Centro de costo")
        self.assertContains(respuesta, "Obligación")
        self.assertContains(respuesta, "Plan de aplicación")
        self.assertContains(respuesta, "Evidencia")
        self.assertContains(respuesta, "Validación")
        self.assertContains(respuesta, "sysadmin_trazabilidad")
        self.assertContains(respuesta, "prevencionista_trazabilidad")
        self.assertContains(respuesta, "Panel administrativo")
        self.assertContains(respuesta, "web")
        self.assertContains(respuesta, "Creó")
        self.assertContains(respuesta, "Modificó")
        self.assertContains(respuesta, "alta")
        self.assertContains(respuesta, "aplicar")
        self.assertContains(respuesta, "cargar_evidencia")
        self.assertContains(respuesta, "validar_evidencia")
        self.assertContains(respuesta, "corrección")
        self.assertContains(
            respuesta,
            "Confirmación equivalente desde el panel administrativo",
        )
        self.assertContains(respuesta, "Datos anteriores")
        self.assertContains(respuesta, "Datos nuevos")

        url_recorrido = reverse(
            "bitacora:recorrido",
            args=[centro.pk, obligacion.pk],
        )
        plan = self.client.get(
            reverse("planes_aplicacion:plan", args=[centro.pk]),
        )
        detalle_evidencia = self.client.get(
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(plan, url_recorrido)
        self.assertContains(detalle_evidencia, url_recorrido)

        acceso_admin = self.client.get(
            reverse("admin:bitacora_eventobitacora_changelist"),
        )
        self.assertEqual(acceso_admin.status_code, 302)

    def test_verifica_el_hash_y_detecta_una_alteracion_del_archivo(self) -> None:
        centro, obligacion, evidencia = self._crear_recorrido()
        self.client.force_login(self.prevencionista)
        url_recorrido = reverse(
            "bitacora:recorrido",
            args=[centro.pk, obligacion.pk],
        )
        url_integridad = reverse(
            "evidencias:verificar_integridad",
            args=[evidencia.pk],
        )

        recorrido = self.client.get(url_recorrido)
        verificacion_original = self.client.get(url_integridad)

        self.assertContains(recorrido, url_integridad)
        self.assertEqual(verificacion_original.status_code, 200)
        self.assertContains(verificacion_original, "Integridad del archivo")
        self.assertContains(verificacion_original, "Coincide")
        self.assertContains(verificacion_original, evidencia.hash_sha256, count=2)

        Path(evidencia.archivo.path).write_bytes(b"archivo alterado")

        verificacion_alterada = self.client.get(url_integridad)

        self.assertEqual(verificacion_alterada.status_code, 200)
        self.assertContains(verificacion_alterada, "No coincide")
        self.assertContains(verificacion_alterada, "Alteración detectada")
        self.assertContains(verificacion_alterada, evidencia.hash_sha256)
        recorrido_actualizado = self.client.get(url_recorrido)
        self.assertContains(recorrido_actualizado, "verificar_integridad", count=2)
        self.assertContains(recorrido_actualizado, "Coincidió")
        self.assertContains(recorrido_actualizado, "No coincidió")

    def test_incluye_eventos_anteriores_a_las_relaciones_del_recorrido(self) -> None:
        centro, obligacion, evidencia = self._crear_recorrido()
        EventoBitacora.objects.create(
            actor=self.prevencionista,
            accion="acto_historico",
            entidad="Evidencia",
            identificador=str(evidencia.pk),
            descripcion="Acto previo a las relaciones explícitas de trazabilidad.",
            canal="web",
        )
        self.client.force_login(self.prevencionista)

        recorrido = self.client.get(
            reverse("bitacora:recorrido", args=[centro.pk, obligacion.pk]),
        )

        self.assertContains(recorrido, "acto_historico")
        self.assertContains(
            recorrido,
            "Acto previo a las relaciones explícitas de trazabilidad",
        )

    def test_los_registros_trazables_no_ofrecen_eliminacion(self) -> None:
        centro, obligacion, evidencia = self._crear_recorrido()
        evento = EventoBitacora.objects.filter(evidencia=evidencia).first()
        assert evento is not None
        cambio = CambioAplicabilidad.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
        ).first()
        assert cambio is not None
        self.client.force_login(self.sysadmin)

        respuestas = (
            self.client.get(
                reverse(
                    "admin:centros_costo_centrocosto_delete",
                    args=[centro.pk],
                ),
            ),
            self.client.get(
                reverse("admin:bitacora_eventobitacora_delete", args=[evento.pk]),
            ),
            self.client.post(
                reverse(
                    "admin:planes_aplicacion_cambioaplicabilidad_change",
                    args=[cambio.pk],
                ),
                {
                    "centro_costo": str(centro.pk),
                    "obligacion": str(obligacion.pk),
                    "motivo": "Intento de sobrescritura",
                    "_save": "Guardar",
                },
            ),
            self.client.get(
                reverse(
                    "admin:planes_aplicacion_cambioaplicabilidad_delete",
                    args=[cambio.pk],
                ),
            ),
            self.client.post(f"/obligaciones/{obligacion.pk}/eliminar/"),
            self.client.post(f"/planes-aplicacion/{centro.pk}/eliminar/"),
            self.client.post(f"/evidencias/{evidencia.pk}/eliminar/"),
        )

        self.assertEqual(
            [respuesta.status_code for respuesta in respuestas],
            [403, 403, 403, 403, 404, 404, 404],
        )
        recorrido = self.client.get(
            reverse("bitacora:recorrido", args=[centro.pk, obligacion.pk]),
        )
        self.assertContains(
            recorrido,
            "Los registros trazables no se editan ni se eliminan",
        )
        self.assertContains(
            recorrido,
            "El registro administrativo de Django no sustituye esta bitácora del dominio",
        )
        self.assertContains(recorrido, "Organismo certificador")
