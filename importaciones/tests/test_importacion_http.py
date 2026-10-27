from io import BytesIO
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion


class ImportacionHttpTests(TestCase):
    def setUp(self) -> None:
        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_importaciones",
            password="clave-segura-de-prueba",
        )
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_importaciones",
            password="clave-segura-de-prueba",
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))

    def _subir(self, tipo: str, contenido: str) -> HttpResponse:
        self.client.force_login(self.sysadmin)
        return cast(
            HttpResponse,
            self.client.post(
                reverse("importaciones:importar"),
                {
                    "tipo": tipo,
                    "archivo": BytesIO(contenido.encode("utf-8")),
                },
            ),
        )

    def test_importa_centros_y_reporta_validas_invalidas_duplicadas_y_franquicia(
        self,
    ) -> None:
        respuesta = self._subir(
            "centros_costo",
            "codigo_contable,nombre,tipo,cve_unidad,es_franquicia\n"
            "FAR-IMP-001,Farmacia Importada,farmacia,CL-1,no\n"
            "FAR-IMP-001,Duplicada,farmacia,CL-2,no\n"
            "ADM-IMP-001,Administración,incorrecto,,no\n"
            "FRA-IMP-001,Franquicia,farmacia,FRA-1,si\n",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Aceptadas: 2")
        self.assertContains(respuesta, "Rechazadas: 1")
        self.assertContains(respuesta, "Duplicadas: 1")
        self.assertContains(respuesta, "Franquicia excluida")
        self.assertEqual(CentroCosto.objects.count(), 2)
        self.assertFalse(
            CentroCosto.objects.get(codigo_contable="FAR-IMP-001").es_franquicia
        )

    def test_importa_obligaciones_y_repite_sin_crear_duplicados(self) -> None:
        contenido = (
            "nombre,norma_origen,titular,periodicidad,clasificacion_evidencia,tipos_centro,motivo\n"
            "Obligación importada,DS 594,centro_costo,anual,general,farmacia,Alta inicial\n"
            "Obligación inválida,DS 594,desconocido,anual,general,,Debe rechazarse\n"
        )
        primera = self._subir("obligaciones", contenido)
        segunda = self._subir("obligaciones", contenido)

        self.assertContains(primera, "Aceptadas: 1")
        self.assertContains(primera, "Rechazadas: 1")
        self.assertContains(segunda, "Duplicadas: 1")
        self.assertContains(segunda, "Rechazadas: 1")
        self.assertEqual(Obligacion.objects.count(), 1)

    def test_prevencionista_puede_importar(self) -> None:
        self.client.force_login(self.prevencionista)
        respuesta = self.client.get(reverse("importaciones:importar"))

        self.assertEqual(respuesta.status_code, 200)

    def test_importacion_rechaza_obligacion_sin_clasificacion_explicita(self) -> None:
        respuesta = self._subir(
            "obligaciones",
            "nombre,norma_origen,titular,periodicidad,tipos_centro,motivo\n"
            "Examen sin clasificar,Fuente ficticia,trabajador,por_evento,,Alta\n",
        )

        self.assertContains(respuesta, "Aceptadas: 0")
        self.assertContains(respuesta, "Rechazadas: 1")
        self.assertFalse(Obligacion.objects.exists())
