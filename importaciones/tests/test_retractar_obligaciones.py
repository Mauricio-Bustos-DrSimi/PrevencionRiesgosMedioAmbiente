"""Retractar lo que se atribuyó al titular equivocado, sin borrar nada.

La situación de partida es la del piloto tal como quedó sembrado antes de que
el trabajador existiera: las dieciocho obligaciones de ADM04 colgando del
centro de costo, catorce de ellas con respaldo por persona. La prueba la arma
aquí en vez de llamar a la siembra, porque la siembra ya no produce ese estado
y lo que hay que corregir es el que quedó escrito.
"""

import tempfile
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from bitacora.models import EventoBitacora
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from evidencias.services import cargar_evidencia, validar_evidencia
from importaciones.catalogo_demo import CATALOGO, NO_APLICAN, SIN_RESPALDO
from importaciones.management.commands.retractar_obligaciones_por_trabajador import (
    CANAL,
)
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad


CLAVE = "clave-segura-de-prueba"

CON_RESPALDO_POR_PERSONA = "Manejo de extintores con simulador"
DEL_CENTRO_DE_COSTO = "Matriz IPER vigente"


@override_settings(DIAS_POR_VENCER=30)
class RetractarObligacionesTests(TestCase):
    def setUp(self) -> None:
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        override = self.settings(MEDIA_ROOT=directorio.name)
        override.enable()
        self.addCleanup(override.disable)

        self.prevencionista = get_user_model().objects.create_user(
            username="prevencion_retractacion",
            password=CLAVE,
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))
        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM04",
            nombre="Bodega de Distribución",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.obligaciones = {
            nombre: self._sembrar_al_centro(nombre)
            for nombre in list(CATALOGO) + list(SIN_RESPALDO) + list(NO_APLICAN)
        }
        self.evidencia = self._cargar_evidencia(CON_RESPALDO_POR_PERSONA)

    # --- la situación que hay que corregir --------------------------------

    def _sembrar_al_centro(self, nombre: str) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=nombre,
            norma_origen="Norma preliminar del piloto",
            titular=TitularObligacion.CENTRO_COSTO,
            periodicidad="anual",
            tipos_centro=[CentroCosto.Tipo.BODEGA],
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta del piloto con periodicidad y norma preliminares.",
        )
        CambioAplicabilidad.objects.create(
            centro_costo=self.centro,
            obligacion=obligacion,
            aplica=nombre not in NO_APLICAN,
            motivo="Aplicabilidad declarada al sembrar el piloto.",
            autor=self.prevencionista,
        )
        return obligacion

    def _cargar_evidencia(self, nombre: str) -> Evidencia:
        evidencia = cargar_evidencia(
            centro=self.centro,
            obligacion=self.obligaciones[nombre],
            actor=self.prevencionista,
            archivo=SimpleUploadedFile(
                "constancia.pdf",
                b"Constancia cargada antes de la retractacion",
                content_type="application/pdf",
            ),
            emisor="Plataforma de capacitación de la empresa",
            fecha_emision=date(2026, 4, 8),
            fecha_vencimiento=date(2027, 4, 8),
            canal="Siembra del piloto",
        )
        validar_evidencia(
            evidencia=evidencia,
            actor=self.prevencionista,
            canal="Siembra del piloto",
        )
        return evidencia

    def _retractar(self, **extra: object) -> str:
        salida = StringIO()
        call_command(
            "retractar_obligaciones_por_trabajador",
            usuario=self.prevencionista.username,
            stdout=salida,
            **extra,
        )
        return salida.getvalue()

    def _version_actual(self, nombre: str) -> VersionObligacion:
        return self.obligaciones[nombre].version_actual

    def _plan(self) -> str:
        self.client.force_login(self.prevencionista)
        respuesta = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.centro.pk])
        )
        return respuesta.content.decode()

    # --- resguardos -------------------------------------------------------

    def test_sin_confirmar_no_escribe_nada(self) -> None:
        salida = self._retractar()

        self.assertIn("No se escribió nada", salida)
        self.assertTrue(
            self.obligaciones[CON_RESPALDO_POR_PERSONA].esta_vigente
        )

    def test_exige_un_prevencionista(self) -> None:
        User.objects.create_user(username="lector", password=CLAVE)

        with self.assertRaises(CommandError) as fallo:
            call_command(
                "retractar_obligaciones_por_trabajador",
                usuario="lector",
                confirmar=True,
            )

        self.assertIn("Prevencionista", str(fallo.exception))
        self.assertTrue(self.obligaciones[CON_RESPALDO_POR_PERSONA].esta_vigente)

    def test_ejecutarla_dos_veces_no_duplica_cierres_ni_falla(self) -> None:
        self._retractar(confirmar=True)
        versiones = self._version_actual(CON_RESPALDO_POR_PERSONA).numero

        salida = self._retractar(confirmar=True)

        self.assertIn("No queda nada por retractar", salida)
        self.assertEqual(
            self._version_actual(CON_RESPALDO_POR_PERSONA).numero,
            versiones,
        )

    # --- lo que la retractación deja --------------------------------------

    def test_cierra_las_catorce_con_respaldo_por_persona(self) -> None:
        self._retractar(confirmar=True)

        cerradas = [
            nombre
            for nombre in CATALOGO
            if not self.obligaciones[nombre].esta_vigente
        ]

        self.assertEqual(len(CATALOGO), 14)
        self.assertCountEqual(cerradas, list(CATALOGO))

    def test_el_cierre_lleva_autor_fecha_y_motivo_de_error_de_atribucion(
        self,
    ) -> None:
        self._retractar(confirmar=True)

        version = self._version_actual(CON_RESPALDO_POR_PERSONA)

        self.assertEqual(version.tipo_version, TipoVersion.CIERRE)
        self.assertEqual(version.autor, self.prevencionista)
        self.assertIsNotNone(version.fecha_cierre)
        self.assertIn("error de atribución", version.motivo)
        self.assertIn("no por cambio normativo", version.motivo)
        self.assertIn("vuelve al plan", version.motivo)

    def test_no_toca_las_obligaciones_que_si_son_del_centro(self) -> None:
        self._retractar(confirmar=True)

        for nombre in list(SIN_RESPALDO) + list(NO_APLICAN):
            with self.subTest(obligacion=nombre):
                self.assertTrue(self.obligaciones[nombre].esta_vigente)

    def test_el_plan_de_adm04_deja_de_exigir_lo_que_no_es_suyo(self) -> None:
        antes = self._plan()
        self.assertIn(CON_RESPALDO_POR_PERSONA, antes)

        self._retractar(confirmar=True)
        despues = self._plan()

        for nombre in CATALOGO:
            with self.subTest(obligacion=nombre):
                self.assertNotIn(nombre, despues)
        for nombre in list(SIN_RESPALDO) + list(NO_APLICAN):
            with self.subTest(obligacion=nombre):
                self.assertIn(nombre, despues)

    def test_cerrar_basta_y_no_agrega_cambios_de_aplicabilidad(self) -> None:
        """Cerrar es suficiente; un «No aplica» diría algo que no es cierto.

        La obligación no dejó de corresponder al centro: nunca fue suya.
        """
        antes = CambioAplicabilidad.objects.count()

        self._retractar(confirmar=True)

        self.assertEqual(CambioAplicabilidad.objects.count(), antes)

    def test_la_evidencia_sigue_consultable_y_verificable(self) -> None:
        self._retractar(confirmar=True)
        self.client.force_login(self.prevencionista)

        detalle = self.client.get(
            reverse("evidencias:validar", args=[self.evidencia.pk])
        )
        integridad = self.client.post(
            reverse("evidencias:verificar_integridad", args=[self.evidencia.pk])
        )

        self.assertContains(detalle, self.evidencia.hash_sha256)
        self.assertContains(integridad, "Coincide")
        self.assertContains(integridad, self.evidencia.hash_sha256)

    def test_cada_cierre_queda_en_la_bitacora_con_su_canal_propio(self) -> None:
        self._retractar(confirmar=True)

        eventos = EventoBitacora.objects.filter(canal=CANAL)

        self.assertEqual(eventos.count(), len(CATALOGO))
        self.assertEqual(
            set(eventos.values_list("accion", flat=True)),
            {"retractar_obligacion"},
        )
        self.assertNotEqual(CANAL, "Siembra del piloto")
        self.assertTrue(
            eventos.filter(
                descripcion__contains=CON_RESPALDO_POR_PERSONA,
                centro_costo=self.centro,
            ).exists()
        )
