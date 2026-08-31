"""El sembrado de la demostración deriva los seis estados de cumplimiento."""

import tempfile
from datetime import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from aceptacion.reloj import reloj_en
from bitacora.models import EventoBitacora
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from evidencias.services import EstadoCumplimiento, caso_de_cumplimiento
from importaciones.catalogo_demo import CATALOGO, SituacionDemo, leer_respaldo
from importaciones.management.commands.sembrar_demo_bodega import (
    CANAL,
    marcador_pdf,
)
from obligaciones.models import Obligacion


# El catálogo fija fechas alrededor de esta jornada; congelarla mantiene la
# prueba estable aunque el calendario avance.
JORNADA = timezone.make_aware(datetime(2026, 8, 31, 9, 0))

ESPERADOS = {
    SituacionDemo.VIGENTE: EstadoCumplimiento.VIGENTE,
    SituacionDemo.POR_VENCER: EstadoCumplimiento.POR_VENCER,
    SituacionDemo.VENCIDO: EstadoCumplimiento.VENCIDO,
    SituacionDemo.PENDIENTE_VALIDACION: EstadoCumplimiento.PENDIENTE_VALIDACION,
    SituacionDemo.SIN_EVIDENCIA: EstadoCumplimiento.SIN_EVIDENCIA,
    SituacionDemo.NO_APLICA: EstadoCumplimiento.NO_APLICA,
}


@override_settings(DIAS_POR_VENCER=30)
class SembrarDemoBodegaTests(TestCase):
    def setUp(self) -> None:
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        override = self.settings(MEDIA_ROOT=directorio.name)
        override.enable()
        self.addCleanup(override.disable)
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencion_demo",
            password="clave-segura-de-prueba",
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))

    def _sembrar(self) -> str:
        salida = StringIO()
        with reloj_en(JORNADA):
            call_command(
                "sembrar_demo_bodega",
                usuario=self.prevencionista.username,
                confirmar=True,
                stdout=salida,
            )
        return salida.getvalue()

    def test_sin_confirmar_no_escribe_nada(self) -> None:
        salida = StringIO()
        call_command(
            "sembrar_demo_bodega",
            usuario=self.prevencionista.username,
            stdout=salida,
        )
        self.assertIn("No se escribió nada", salida.getvalue())
        self.assertFalse(CentroCosto.objects.exists())
        self.assertFalse(Evidencia.objects.exists())

    def test_exige_un_prevencionista(self) -> None:
        User.objects.create_user(username="lector", password="clave-segura-de-prueba")
        with self.assertRaises(CommandError) as fallo:
            call_command("sembrar_demo_bodega", usuario="lector", confirmar=True)
        self.assertIn("Prevencionista", str(fallo.exception))
        self.assertFalse(CentroCosto.objects.exists())

    def test_se_niega_a_sembrar_dos_veces(self) -> None:
        self._sembrar()
        with self.assertRaises(CommandError) as fallo:
            self._sembrar()
        self.assertIn("append-only", str(fallo.exception))

    def test_cada_obligacion_deriva_el_estado_que_la_demo_quiere_mostrar(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")
        respaldo = leer_respaldo()

        observados: dict[str, EstadoCumplimiento] = {}
        for curso in respaldo.cursos:
            caso = caso_de_cumplimiento(
                centro=centro,
                obligacion=self._obligacion(curso.nombre),
                en_fecha=JORNADA.date(),
            )
            assert caso is not None, f"{curso.nombre} quedó fuera del plan."
            observados[curso.nombre] = caso.estado

        for curso in respaldo.cursos:
            with self.subTest(curso=curso.nombre):
                esperado = ESPERADOS[CATALOGO[curso.nombre].situacion]
                self.assertEqual(observados[curso.nombre], esperado)

        self.assertEqual(
            set(observados.values()),
            set(EstadoCumplimiento),
            "La demostración debe exhibir los seis estados de cumplimiento.",
        )

    def _obligacion(self, nombre: str) -> Obligacion:
        for obligacion in Obligacion.objects.all():
            if obligacion.version_actual.nombre == nombre:
                return obligacion
        self.fail(f"No se sembró la obligación {nombre}.")

    def test_la_bitacora_declara_que_los_actos_son_una_siembra(self) -> None:
        self._sembrar()
        canales = set(EventoBitacora.objects.values_list("canal", flat=True))
        self.assertEqual(canales, {CANAL})
        self.assertTrue(
            EventoBitacora.objects.filter(
                descripcion="Creó el centro de costo Bodega de Distribución."
            ).exists()
        )

    def test_los_archivos_quedan_marcados_como_demostracion(self) -> None:
        self._sembrar()
        self.assertTrue(Evidencia.objects.exists())
        for evidencia in Evidencia.objects.all():
            with self.subTest(evidencia=evidencia.pk):
                self.assertIn("no es evidencia real", evidencia.emisor)
                with evidencia.archivo.open("rb") as archivo:
                    contenido = archivo.read()
                self.assertTrue(contenido.startswith(b"%PDF-"))
                self.assertIn(b"NO ES EVIDENCIA REAL", contenido)

    def test_el_marcador_es_un_pdf_con_tabla_de_referencias_correcta(self) -> None:
        contenido = marcador_pdf(["Una línea", "Otra (con paréntesis)"])
        inicio = int(contenido.split(b"startxref\n")[1].split(b"\n")[0])
        self.assertEqual(contenido[inicio : inicio + 4], b"xref")
        self.assertTrue(contenido.rstrip().endswith(b"%%EOF"))
