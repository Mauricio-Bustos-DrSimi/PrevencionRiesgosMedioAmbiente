from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from centros_costo.models import CentroCosto


CLAVE_PRUEBA = "clave-segura-de-prueba"


class CentrosCostoHttpTests(TestCase):
    def setUp(self) -> None:
        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_centros",
            password=CLAVE_PRUEBA,
        )

    def _crear_desde_admin(
        self,
        *,
        codigo_contable: str = "FAR-001",
        nombre: str = "Farmacia Alameda",
        tipo: str = "farmacia",
        cve_unidad: str = "CL-101",
        es_franquicia: bool = False,
        continuar: bool = False,
    ) -> HttpResponse:
        datos: dict[str, str] = {
            "codigo_contable": codigo_contable,
            "nombre": nombre,
            "tipo": tipo,
            "cve_unidad": cve_unidad,
            "_continue" if continuar else "_save": "Guardar",
        }
        if es_franquicia:
            datos["es_franquicia"] = "on"
        return cast(
            HttpResponse,
            self.client.post(
                reverse("admin:centros_costo_centrocosto_add"),
                datos,
            ),
        )

    def _iniciar_como_prevencionista(self) -> None:
        prevencionista = get_user_model().objects.create_user(
            username="prevencionista_centros",
            password=CLAVE_PRUEBA,
        )
        prevencionista.groups.add(Group.objects.get(name="Prevencionista"))
        self.client.force_login(prevencionista)

    def test_sysadmin_registra_los_tres_tipos_y_prevencionista_los_consulta(
        self,
    ) -> None:
        self.client.force_login(self.sysadmin)
        altas = (
            {
                "codigo_contable": "FAR-001",
                "nombre": "Farmacia Alameda",
                "tipo": "farmacia",
                "cve_unidad": "CL-101",
            },
            {
                "codigo_contable": "ADM-001",
                "nombre": "Centro administrativo Santiago",
                "tipo": "centro_administrativo",
                "cve_unidad": "",
            },
            {
                "codigo_contable": "BOD-001",
                "nombre": "Bodega Central",
                "tipo": "bodega",
                "cve_unidad": "CL-301",
            },
        )

        for alta in altas:
            respuesta = self.client.post(
                reverse("admin:centros_costo_centrocosto_add"),
                {**alta, "_save": "Guardar"},
            )
            self.assertEqual(respuesta.status_code, 302)

        self._iniciar_como_prevencionista()

        respuesta_lista = self.client.get("/centros-de-costo/")

        self.assertEqual(respuesta_lista.status_code, 200)
        self.assertContains(respuesta_lista, "FAR-001")
        self.assertContains(respuesta_lista, "Farmacia Alameda")
        self.assertContains(respuesta_lista, "Farmacia")
        self.assertContains(respuesta_lista, "CL-101")
        self.assertContains(respuesta_lista, "ADM-001")
        self.assertContains(respuesta_lista, "Centro administrativo")
        self.assertContains(respuesta_lista, "BOD-001")
        self.assertContains(respuesta_lista, "Bodega")

    def test_codigo_contable_es_unico_y_cveunidad_es_opcional(self) -> None:
        self.client.force_login(self.sysadmin)
        primera_alta = self._crear_desde_admin(cve_unidad="")
        alta_duplicada = self._crear_desde_admin(
            nombre="Otra farmacia",
            cve_unidad="CL-999",
        )
        self._iniciar_como_prevencionista()

        respuesta_lista = self.client.get("/centros-de-costo/")

        self.assertEqual(primera_alta.status_code, 302)
        self.assertEqual(alta_duplicada.status_code, 200)
        self.assertContains(
            alta_duplicada,
            "Ya existe Centro de costo con este Código contable oficial.",
        )
        self.assertContains(respuesta_lista, "FAR-001", count=1)
        self.assertContains(respuesta_lista, "Farmacia Alameda")
        self.assertNotContains(respuesta_lista, "Otra farmacia")
        self.assertContains(respuesta_lista, "—")

    def test_franquicia_explicita_no_es_operable_en_lista_ni_detalle(self) -> None:
        centro_incluido = CentroCosto.objects.create(
            codigo_contable="FAR-001",
            nombre="Farmacia Alameda",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        franquicia = CentroCosto.objects.create(
            codigo_contable="FRA-001",
            nombre="Franquicia Providencia",
            tipo=CentroCosto.Tipo.FARMACIA,
            es_franquicia=True,
        )
        self._iniciar_como_prevencionista()

        respuesta_lista = self.client.get("/centros-de-costo/")
        respuesta_detalle = self.client.get(
            f"/centros-de-costo/{centro_incluido.pk}/",
        )
        respuesta_franquicia = self.client.get(
            f"/centros-de-costo/{franquicia.pk}/",
        )

        self.assertContains(respuesta_lista, "FAR-001")
        self.assertNotContains(respuesta_lista, "FRA-001")
        self.assertEqual(respuesta_detalle.status_code, 200)
        self.assertContains(respuesta_detalle, "Código contable oficial")
        self.assertContains(respuesta_detalle, "FAR-001")
        self.assertEqual(respuesta_franquicia.status_code, 404)

    def test_consulta_requiere_rol_prevencionista_o_sysadmin(self) -> None:
        usuario_sin_rol = get_user_model().objects.create_user(
            username="sin_rol_centros",
            password=CLAVE_PRUEBA,
        )

        respuesta_anonima = self.client.get("/centros-de-costo/")
        self.client.force_login(usuario_sin_rol)
        respuesta_sin_rol = self.client.get("/centros-de-costo/")
        self.client.force_login(self.sysadmin)
        respuesta_sysadmin = self.client.get("/centros-de-costo/")

        self.assertRedirects(
            respuesta_anonima,
            "/cuentas/iniciar-sesion/?next=/centros-de-costo/",
            fetch_redirect_response=False,
        )
        self.assertEqual(respuesta_sin_rol.status_code, 403)
        self.assertEqual(respuesta_sysadmin.status_code, 200)

    def test_admin_no_ofrece_borrado_de_centros_de_costo(self) -> None:
        centro = CentroCosto.objects.create(
            codigo_contable="BOD-001",
            nombre="Bodega Central",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.client.force_login(self.sysadmin)

        respuesta_eliminar = self.client.get(
            reverse(
                "admin:centros_costo_centrocosto_delete",
                args=[centro.pk],
            ),
        )

        self.assertEqual(respuesta_eliminar.status_code, 403)

    def test_alta_y_cambio_aparecen_en_la_bitacora_del_dominio(self) -> None:
        self.client.force_login(self.sysadmin)
        respuesta_alta = self._crear_desde_admin(continuar=True)
        url_cambio = respuesta_alta.headers["Location"]

        respuesta_cambio = self.client.post(
            url_cambio,
            {
                "codigo_contable": "FAR-001",
                "nombre": "Farmacia Alameda Centro",
                "tipo": "farmacia",
                "cve_unidad": "CL-101",
                "_save": "Guardar",
            },
        )
        respuesta_bitacora = self.client.get(
            reverse("admin:bitacora_eventobitacora_changelist"),
        )

        self.assertEqual(respuesta_alta.status_code, 302)
        self.assertEqual(respuesta_cambio.status_code, 302)
        self.assertContains(respuesta_bitacora, "Creó")
        self.assertContains(respuesta_bitacora, "Modificó")
        self.assertContains(
            respuesta_bitacora,
            '<th class="field-ocurrido_en nowrap"><a href=',
            count=2,
            html=False,
        )
        self.assertContains(
            respuesta_bitacora,
            '<td class="field-entidad">Centro de costo</td>',
            count=2,
            html=False,
        )
        self.assertContains(
            respuesta_bitacora,
            '<td class="field-identificador">FAR-001</td>',
            count=2,
            html=False,
        )
        self.assertContains(
            respuesta_bitacora,
            '<td class="field-actor nowrap">sysadmin_centros</td>',
            count=2,
            html=False,
        )
        self.assertContains(
            respuesta_bitacora,
            '<td class="field-canal">Panel administrativo</td>',
            count=2,
            html=False,
        )
