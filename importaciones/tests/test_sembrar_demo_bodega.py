"""La siembra del piloto atribuye cada constancia a la persona que la obtuvo.

El respaldo del departamento son 245 constancias de 129 trabajadores. Antes se
cargaba una por obligación —la que caduca primero— colgada del centro de costo,
y así no se podía saber quién estaba cubierto ni cuántos faltaban. Ahora se
cargan todas, cada una a nombre del trabajador cuyo RUT nombra su carpeta.

La carpeta de estas pruebas es sintética y pequeña, pero tiene la forma de la
real: varios cursos, varias personas, un mismo RUT escrito de dos maneras, y
escaneos sin capa de texto.
"""

import tempfile
from datetime import date, datetime
from io import StringIO
from pathlib import Path

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
from evidencias.services import (
    EstadoCumplimiento,
    caso_de_cumplimiento,
    caso_de_trabajador,
)
from importaciones.catalogo_demo import CATALOGO, NO_APLICAN, SIN_RESPALDO
from importaciones.lectura_constancias import leer_resumen
from importaciones.management.commands.sembrar_demo_bodega import CANAL
from importaciones.pdf import marcador_pdf
from obligaciones.models import Obligacion, TitularObligacion
from trabajadores.models import Trabajador


# La jornada en que se prepara la demostración. Se congela para que la prueba
# no dependa del día en que se ejecute.
JORNADA = timezone.make_aware(datetime(2026, 8, 31, 9, 0))

EXTINTORES = "Manejo de extintores con simulador"
ALTURA = "Examen ocupacional de altura física"
PSICOSOCIALES = "Fortalecimiento de competencias psicosociales"

AUXILIARES = "Auxiliares de bodegas Nivel operativo"
JEFATURAS = "Jefaturas de bodegas"

# El texto que dibujan las constancias de la plataforma, tal como aparece.
FECHADA = [
    "USO Y MANEJO DE EXTINTORES",
    "REALIZADO: 08 DE ABRIL DE 2024 - DURACION: 2 HORAS",
    "CODIGO: ABC ---- FECHA EXPIRACION: 08/04/2027",
]
SIN_FECHA = ["ESCANEO DE CLINICA SIN CAPA DE TEXTO"]


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
        self.carpeta = self._carpeta_de_respaldo()

    # --- la carpeta de respaldo -------------------------------------------

    def _archivo(self, ruta: str, lineas: list[str]) -> None:
        destino = self.carpeta / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(marcador_pdf(lineas))

    def _carpeta_de_respaldo(self) -> Path:
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.carpeta = Path(directorio.name)
        # Dos auxiliares con su constancia de extintores, uno de ellos con el
        # examen de altura sin fecha. Una jefatura con psicosociales, escrita
        # con otro separador y con el nombre truncado en una de sus carpetas.
        self._archivo(
            f"3. {AUXILIARES}/1. Uso y manejo de extintores/"
            "11111111-1 - Prueba Prueba Una/Diploma_1.pdf",
            FECHADA,
        )
        self._archivo(
            f"3. {AUXILIARES}/1. Uso y manejo de extintores/"
            "22222222-2 - Prueba Prueba Dos/Diploma_2.pdf",
            FECHADA,
        )
        self._archivo(
            f"3. {AUXILIARES}/3. Examenes Ocupacionales/1. Altura Fisica/"
            "11111111-1 - Prueba Prueba Una/Informe_11111111-1_2026.pdf",
            SIN_FECHA,
        )
        self._archivo(
            f"1. {JEFATURAS}/2. Fortaleciendo Competencias psicosociales/"
            "33333333-3 -Prueba Prueba Tres Apellido Largo/Diploma_3.pdf",
            FECHADA,
        )
        self._archivo(
            f"1. {JEFATURAS}/1. Uso y manejo de extintores/"
            "33333333-3 - Prueba Prueba Tres/Diploma_4.pdf",
            FECHADA,
        )
        return self.carpeta

    # --- utilidades -------------------------------------------------------

    def _sembrar(self, **extra: object) -> str:
        salida = StringIO()
        opciones: dict[str, object] = {"carpeta": str(self.carpeta), "confirmar": True}
        opciones.update(extra)
        with reloj_en(JORNADA):
            call_command(
                "sembrar_demo_bodega",
                usuario=self.prevencionista.username,
                stdout=salida,
                **opciones,
            )
        return salida.getvalue()

    def _obligacion(self, nombre: str) -> Obligacion:
        for obligacion in Obligacion.objects.all():
            if obligacion.version_actual.nombre == nombre:
                return obligacion
        self.fail(f"No se sembró la obligación {nombre}.")

    def _trabajador(self, rut: str) -> Trabajador:
        return Trabajador.objects.get(rut=rut)

    def _estado_del_centro(self, nombre: str) -> EstadoCumplimiento | None:
        centro = CentroCosto.objects.get(codigo_contable="ADM04")
        caso = caso_de_cumplimiento(
            centro=centro,
            obligacion=self._obligacion(nombre),
            en_fecha=JORNADA.date(),
        )
        return None if caso is None else caso.estado

    def _estado_de(self, rut: str, nombre: str) -> EstadoCumplimiento | None:
        caso = caso_de_trabajador(
            trabajador=self._trabajador(rut),
            obligacion=self._obligacion(nombre),
            en_fecha=JORNADA.date(),
        )
        return None if caso is None else caso.estado

    # --- resguardos -------------------------------------------------------

    def test_sin_confirmar_no_escribe_nada(self) -> None:
        salida = self._sembrar(confirmar=False)

        self.assertIn("No se escribió nada", salida)
        self.assertFalse(CentroCosto.objects.exists())
        self.assertFalse(Trabajador.objects.exists())
        self.assertFalse(Evidencia.objects.exists())

    def test_exige_un_prevencionista(self) -> None:
        User.objects.create_user(username="lector", password="clave-segura-de-prueba")

        with self.assertRaises(CommandError) as fallo:
            call_command(
                "sembrar_demo_bodega",
                usuario="lector",
                carpeta=str(self.carpeta),
                confirmar=True,
            )

        self.assertIn("Prevencionista", str(fallo.exception))
        self.assertFalse(CentroCosto.objects.exists())

    def test_se_niega_a_sembrar_dos_veces(self) -> None:
        self._sembrar()

        with self.assertRaises(CommandError) as fallo:
            self._sembrar()

        self.assertIn("append-only", str(fallo.exception))

    def test_una_carpeta_inexistente_se_dice_antes_de_escribir(self) -> None:
        with self.assertRaises(CommandError):
            self._sembrar(carpeta="carpeta-que-no-existe")

        self.assertFalse(CentroCosto.objects.exists())

    def test_sin_la_carpeta_se_niega_a_atribuir_en_vez_de_degradar(self) -> None:
        """El resumen versionado es anónimo: no basta para atribuir.

        Degradar en silencio a la carga por centro de costo reproduciría el
        error que esta iniciativa vino a corregir.
        """
        with self.assertRaises(CommandError) as fallo:
            self._sembrar(carpeta=None)

        mensaje = str(fallo.exception)
        self.assertIn("--carpeta", mensaje)
        self.assertIn("anónimo", mensaje)
        self.assertIn(EXTINTORES, mensaje)
        self.assertFalse(CentroCosto.objects.exists())
        self.assertFalse(Trabajador.objects.exists())

    def test_una_constancia_sin_rut_legible_detiene_la_siembra(self) -> None:
        self._archivo(
            f"1. {JEFATURAS}/1. Uso y manejo de extintores/"
            "Sin identificacion/Diploma_9.pdf",
            FECHADA,
        )

        with self.assertRaises(CommandError) as fallo:
            self._sembrar()

        self.assertIn("no dicen a quién pertenecen", str(fallo.exception))
        self.assertFalse(Trabajador.objects.exists())

    # --- la atribución ----------------------------------------------------

    def test_el_titular_sale_del_catalogo_obligacion_por_obligacion(self) -> None:
        self._sembrar()

        for nombre in CATALOGO:
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._obligacion(nombre).version_actual.titular,
                    TitularObligacion.TRABAJADOR,
                )
        for nombre in list(SIN_RESPALDO) + list(NO_APLICAN):
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._obligacion(nombre).version_actual.titular,
                    TitularObligacion.CENTRO_COSTO,
                )

    def test_los_catorce_tipos_de_documento_nacen_del_trabajador(self) -> None:
        self.assertEqual(len(CATALOGO), 14)

    def test_se_cargan_todas_las_constancias_y_no_una_por_obligacion(self) -> None:
        self._sembrar()

        self.assertEqual(Evidencia.objects.count(), 5)
        self.assertEqual(
            Evidencia.objects.filter(
                obligacion=self._obligacion(EXTINTORES),
            ).count(),
            3,
        )

    def test_cada_constancia_queda_a_nombre_de_su_titular(self) -> None:
        self._sembrar()

        for evidencia in Evidencia.objects.all():
            with self.subTest(evidencia=evidencia.pk):
                self.assertIsNotNone(evidencia.trabajador)
        extintores = Evidencia.objects.filter(
            obligacion=self._obligacion(EXTINTORES),
        )
        self.assertCountEqual(
            [evidencia.trabajador.rut for evidencia in extintores if evidencia.trabajador],
            ["11111111-1", "22222222-2", "33333333-3"],
        )

    def test_da_de_alta_a_los_trabajadores_con_el_cargo_de_su_carpeta(self) -> None:
        self._sembrar()

        self.assertEqual(Trabajador.objects.count(), 3)
        self.assertEqual(self._trabajador("11111111-1").cargo, AUXILIARES)
        self.assertEqual(self._trabajador("33333333-3").cargo, JEFATURAS)
        centro = CentroCosto.objects.get(codigo_contable="ADM04")
        for trabajador in Trabajador.objects.all():
            with self.subTest(trabajador=trabajador.rut):
                self.assertEqual(trabajador.centro_costo_actual, centro)
                self.assertTrue(trabajador.esta_validado())

    def test_la_misma_persona_en_varios_cursos_es_un_solo_trabajador(self) -> None:
        self._sembrar()

        tres = Trabajador.objects.filter(rut="33333333-3")

        self.assertEqual(tres.count(), 1)
        # De las dos escrituras de su carpeta manda la más larga: la otra viene
        # truncada, y el nombre no es la identidad.
        self.assertEqual(tres.get().nombre, "Prueba Prueba Tres Apellido Largo")

    def test_las_constancias_sin_fecha_quedan_pendientes_una_por_persona(self) -> None:
        self._sembrar()

        self.assertEqual(
            self._estado_de("11111111-1", ALTURA),
            EstadoCumplimiento.PENDIENTE_VALIDACION,
        )
        pendientes = Evidencia.objects.filter(validacion__isnull=True)
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.get().trabajador, self._trabajador("11111111-1"))

    def test_el_estado_se_deriva_persona_por_persona(self) -> None:
        self._sembrar()

        # La constancia de extintores es de abril de 2024 y el ciclo declarado
        # es anual: quien la tiene está vencido, quien no la tiene está sin
        # evidencia. Nadie escribió ninguno de los dos estados.
        self.assertEqual(
            self._estado_de("11111111-1", EXTINTORES),
            EstadoCumplimiento.VENCIDO,
        )
        self.assertEqual(
            self._estado_de("22222222-2", ALTURA),
            EstadoCumplimiento.SIN_EVIDENCIA,
        )

    def test_el_centro_ve_el_agregado_de_su_dotacion(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        caso = caso_de_cumplimiento(
            centro=centro,
            obligacion=self._obligacion(ALTURA),
            en_fecha=JORNADA.date(),
        )

        assert caso is not None
        # Peor estado presente: uno pendiente de validación y uno sin evidencia.
        self.assertEqual(caso.estado, EstadoCumplimiento.SIN_EVIDENCIA)
        self.assertEqual(dict(caso.recuento)[EstadoCumplimiento.SIN_EVIDENCIA], 1)
        self.assertEqual(
            dict(caso.recuento)[EstadoCumplimiento.PENDIENTE_VALIDACION],
            1,
        )

    def test_lo_que_el_respaldo_no_cubre_queda_sin_evidencia(self) -> None:
        self._sembrar()

        for nombre in SIN_RESPALDO:
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._estado_del_centro(nombre),
                    EstadoCumplimiento.SIN_EVIDENCIA,
                )

    def test_lo_que_no_le_toca_a_la_bodega_queda_declarado(self) -> None:
        self._sembrar()

        for nombre in NO_APLICAN:
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._estado_del_centro(nombre),
                    EstadoCumplimiento.NO_APLICA,
                )

    # --- fidelidad al respaldo --------------------------------------------

    def test_carga_las_fechas_que_declara_la_constancia(self) -> None:
        self._sembrar()

        evidencia = Evidencia.objects.get(
            obligacion=self._obligacion(EXTINTORES),
            trabajador=self._trabajador("11111111-1"),
        )

        self.assertEqual(evidencia.fecha_emision, date(2024, 4, 8))
        self.assertEqual(evidencia.fecha_vencimiento, date(2027, 4, 8))

    def test_guarda_la_constancia_original_y_no_un_marcador(self) -> None:
        self._sembrar()

        evidencia = Evidencia.objects.get(
            obligacion=self._obligacion(EXTINTORES),
            trabajador=self._trabajador("11111111-1"),
        )
        with evidencia.archivo.open("rb") as archivo:
            contenido = archivo.read()

        self.assertTrue(contenido.startswith(b"%PDF-"))
        self.assertIn(b"USO Y MANEJO DE EXTINTORES", contenido)

    def test_el_resumen_versionado_sigue_sin_nombres_ni_rut(self) -> None:
        rendido = repr(leer_resumen())

        self.assertNotIn("Prueba", rendido)
        self.assertNotRegex(rendido, r"\d{7,8}-[\dkK]")

    def test_el_resumen_versionado_describe_todo_el_catalogo(self) -> None:
        # Si la carpeta gana un curso que el catálogo no describe, la siembra
        # tiene que detenerse en vez de inventarle una norma.
        faltantes = [
            curso.nombre
            for curso in leer_resumen().cursos
            if curso.nombre not in CATALOGO
        ]

        self.assertEqual(faltantes, [])

    # --- trazabilidad -----------------------------------------------------

    def test_la_bitacora_declara_de_donde_vienen_los_actos(self) -> None:
        self._sembrar()

        canales = set(EventoBitacora.objects.values_list("canal", flat=True))

        self.assertEqual(canales, {CANAL})
        self.assertTrue(
            EventoBitacora.objects.filter(
                descripcion="Creó el centro de costo Bodega de Distribución."
            ).exists()
        )
        self.assertTrue(
            EventoBitacora.objects.filter(
                accion="alta_trabajador",
                identificador="11111111-1",
            ).exists()
        )

    def test_la_periodicidad_queda_declarada_como_no_confirmada(self) -> None:
        self._sembrar()

        for obligacion in Obligacion.objects.all():
            with self.subTest(obligacion=str(obligacion)):
                self.assertIn("preliminares", obligacion.version_actual.motivo)
