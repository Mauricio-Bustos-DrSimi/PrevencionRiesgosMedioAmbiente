from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class CatalogoObligacionesTests(TestCase):
    def setUp(self) -> None:
        grupo = Group.objects.get(name="Prevencionista")
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_catalogo",
            password="clave-segura-de-prueba",
        )
        self.prevencionista.groups.add(grupo)
        self.client.force_login(self.prevencionista)

    def _registrar_obligacion(self) -> str:
        respuesta = self.client.post(
            reverse("obligaciones:crear"),
            {
                "nombre": "Mantener extintores certificados",
                "norma_origen": "DS 594, artículo 45",
                "titular": "centro_costo",
                "periodicidad": "anual",
                "motivo": "Incorporación del catálogo inicial",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        return respuesta.headers["Location"]

    def test_prevencionista_registra_y_consulta_una_obligacion_vigente(self) -> None:
        respuesta_alta = self._registrar_obligacion()

        self.assertRegex(respuesta_alta, r"/obligaciones/\d+/")
        respuesta_catalogo = self.client.get(reverse("obligaciones:catalogo"))
        self.assertContains(respuesta_catalogo, "Mantener extintores certificados")
        self.assertContains(respuesta_catalogo, "DS 594, artículo 45")
        self.assertContains(respuesta_catalogo, "Centro de costo")
        self.assertContains(respuesta_catalogo, "Anual")

    def test_correccion_crea_una_version_y_conserva_la_anterior(self) -> None:
        detalle = self._registrar_obligacion()

        respuesta_correccion = self.client.post(
            f"{detalle}corregir/",
            {
                "nombre": "Mantener extintores con certificación vigente",
                "norma_origen": "DS 594, artículos 45 y 48",
                "titular": "centro_costo",
                "periodicidad": "anual",
                "motivo": "Se incorporó la referencia al artículo 48",
            },
        )

        self.assertRedirects(respuesta_correccion, detalle)
        respuesta_detalle = self.client.get(detalle)
        self.assertContains(respuesta_detalle, "Versión 1")
        self.assertContains(respuesta_detalle, "DS 594, artículo 45")
        self.assertContains(respuesta_detalle, "Versión 2")
        self.assertContains(respuesta_detalle, "DS 594, artículos 45 y 48")
        self.assertContains(
            respuesta_detalle,
            "Se incorporó la referencia al artículo 48",
        )

    def test_cierre_exige_fecha_y_motivo_y_retira_la_obligacion_del_catalogo(self) -> None:
        detalle = self._registrar_obligacion()

        respuesta_incompleta = self.client.post(
            f"{detalle}cerrar/",
            {"fecha_cierre": "", "motivo": ""},
        )

        self.assertEqual(respuesta_incompleta.status_code, 200)
        self.assertContains(respuesta_incompleta, "Este campo es obligatorio", count=2)
        self.assertContains(
            self.client.get(reverse("obligaciones:catalogo")),
            "Mantener extintores certificados",
        )

        respuesta_cierre = self.client.post(
            f"{detalle}cerrar/",
            {
                "fecha_cierre": "2026-08-27",
                "motivo": "La nueva norma reemplazó esta obligación",
            },
        )

        self.assertRedirects(respuesta_cierre, detalle)
        respuesta_detalle = self.client.get(detalle)
        self.assertContains(respuesta_detalle, "Versión 2")
        self.assertContains(respuesta_detalle, "Cierre")
        self.assertContains(respuesta_detalle, "27 de agosto de 2026")
        self.assertContains(respuesta_detalle, "prevencionista_catalogo")
        self.assertNotContains(respuesta_detalle, ">Corregir<")
        self.assertNotContains(respuesta_detalle, ">Cerrar<")
        self.assertNotContains(
            self.client.get(reverse("obligaciones:catalogo")),
            "Mantener extintores certificados",
        )

    def test_operacion_mvp_solo_ofrece_centro_de_costo_como_titular(self) -> None:
        respuesta = self.client.get(reverse("obligaciones:crear"))

        self.assertContains(respuesta, 'value="centro_costo"')
        self.assertNotContains(respuesta, 'value="trabajador"')
        self.assertNotContains(respuesta, 'value="externo"')
        self.assertNotContains(respuesta, 'value="empresa"')
        self.assertContains(
            respuesta,
            "El modelo reconoce como titulares al centro de costo, trabajador, externo y empresa",
        )

    def test_no_hay_operacion_http_para_eliminar_una_obligacion(self) -> None:
        detalle = self._registrar_obligacion()

        respuesta = self.client.post(f"{detalle}eliminar/")

        self.assertEqual(respuesta.status_code, 404)

    def test_usuario_sin_rol_no_puede_administrar_el_catalogo(self) -> None:
        usuario = get_user_model().objects.create_user(username="sin_rol")
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse("obligaciones:catalogo"))

        self.assertEqual(respuesta.status_code, 403)

    def test_sysadmin_opera_el_catalogo_y_observa_los_actos_en_la_bitacora(self) -> None:
        sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_catalogo",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)
        detalle = self._registrar_obligacion()
        self.client.post(
            f"{detalle}corregir/",
            {
                "nombre": "Mantener extintores con certificación vigente",
                "norma_origen": "DS 594, artículos 45 y 48",
                "titular": "centro_costo",
                "periodicidad": "anual",
                "motivo": "Corrección trazable",
            },
        )
        self.client.post(
            f"{detalle}cerrar/",
            {"fecha_cierre": "2026-08-27", "motivo": "Cierre trazable"},
        )

        respuesta_bitacora = self.client.get("/admin/bitacora/eventobitacora/")

        self.assertEqual(respuesta_bitacora.status_code, 200)
        self.assertContains(respuesta_bitacora, "sysadmin_catalogo")
        self.assertContains(respuesta_bitacora, "alta")
        self.assertContains(respuesta_bitacora, "corrección")
        self.assertContains(respuesta_bitacora, "cierre")
        self.assertContains(respuesta_bitacora, "obligación")
        self.assertContains(respuesta_bitacora, "web")
        respuesta_admin = self.client.get("/admin/obligaciones/obligacion/")
        self.assertEqual(respuesta_admin.status_code, 200)
        self.assertContains(
            respuesta_admin,
            reverse("admin:obligaciones_obligacion_add"),
        )
