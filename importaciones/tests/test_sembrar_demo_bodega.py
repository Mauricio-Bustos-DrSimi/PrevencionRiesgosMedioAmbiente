"""La siembra del piloto deriva los estados desde las fechas reales del respaldo."""

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
from evidencias.services import EstadoCumplimiento, caso_de_cumplimiento
from importaciones.catalogo_demo import CATALOGO, NO_APLICAN, SIN_RESPALDO
from importaciones.lectura_constancias import leer_resumen
from importaciones.management.commands.sembrar_demo_bodega import CANAL
from importaciones.pdf import marcador_pdf
from obligaciones.models import Obligacion


# La jornada en que se prepara la demostración. Se congela para que la prueba
# no dependa del día en que se ejecute.
JORNADA = timezone.make_aware(datetime(2026, 8, 31, 9, 0))

# Lo que el respaldo real del departamento produce a esa fecha. No se calcula:
# se escribe, para que la prueba falle si el catálogo o la lectura cambian el
# resultado sin que nadie lo haya decidido.
ESPERADOS: dict[str, EstadoCumplimiento] = {
    # Constancias de 2024 contra ciclos anuales o bienales.
    "Manejo de extintores con simulador": EstadoCumplimiento.VENCIDO,
    "Fortalecimiento de competencias psicosociales": EstadoCumplimiento.VENCIDO,
    "Orientación en prevención de riesgos laborales": EstadoCumplimiento.VENCIDO,
    # La única cuyo ciclo anual termina justo en la jornada.
    "Factores de riesgo MMC": EstadoCumplimiento.POR_VENCER,
    # Capacitaciones recientes, todavía dentro del ciclo.
    "Prevención del consumo de alcohol y drogas": EstadoCumplimiento.VIGENTE,
    "Análisis del Decreto Supremo 44": EstadoCumplimiento.VIGENTE,
    "Liderazgo en seguridad y salud para supervisores": EstadoCumplimiento.VIGENTE,
    "Factores de riesgo TMERT": EstadoCumplimiento.VIGENTE,
    "Gestión del riesgo de desastre": EstadoCumplimiento.VIGENTE,
    # Escaneos sin capa de texto: la fecha la tiene que confirmar Prevención.
    "Examen ocupacional de altura física": EstadoCumplimiento.PENDIENTE_VALIDACION,
    "Examen ocupacional de conductor clase D": EstadoCumplimiento.PENDIENTE_VALIDACION,
    "Examen ocupacional de operadores de maquinaria": (
        EstadoCumplimiento.PENDIENTE_VALIDACION
    ),
    "Examen ocupacional de conductor de vehículo liviano": (
        EstadoCumplimiento.PENDIENTE_VALIDACION
    ),
    "Licencia de conducir": EstadoCumplimiento.PENDIENTE_VALIDACION,
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

    def _sembrar(self, **extra: object) -> str:
        salida = StringIO()
        with reloj_en(JORNADA):
            call_command(
                "sembrar_demo_bodega",
                usuario=self.prevencionista.username,
                confirmar=True,
                stdout=salida,
                **extra,
            )
        return salida.getvalue()

    def _obligacion(self, nombre: str) -> Obligacion:
        for obligacion in Obligacion.objects.all():
            if obligacion.version_actual.nombre == nombre:
                return obligacion
        self.fail(f"No se sembró la obligación {nombre}.")

    def _estado(self, centro: CentroCosto, nombre: str) -> EstadoCumplimiento:
        caso = caso_de_cumplimiento(
            centro=centro,
            obligacion=self._obligacion(nombre),
            en_fecha=JORNADA.date(),
        )
        assert caso is not None, f"{nombre} quedó fuera del plan de aplicación."
        return caso.estado

    # --- resguardos -------------------------------------------------------

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

    def test_una_carpeta_inexistente_se_dice_antes_de_escribir(self) -> None:
        with self.assertRaises(CommandError):
            self._sembrar(carpeta="carpeta-que-no-existe")

        self.assertFalse(CentroCosto.objects.exists())

    # --- lo que la demostración muestra -----------------------------------

    def test_cada_obligacion_deriva_el_estado_que_su_respaldo_implica(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        for nombre, esperado in ESPERADOS.items():
            with self.subTest(obligacion=nombre):
                self.assertEqual(self._estado(centro, nombre), esperado)

    def test_lo_que_el_respaldo_no_cubre_queda_sin_evidencia(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        for nombre in SIN_RESPALDO:
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._estado(centro, nombre),
                    EstadoCumplimiento.SIN_EVIDENCIA,
                )

    def test_lo_que_no_le_toca_a_la_bodega_queda_declarado(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        for nombre in NO_APLICAN:
            with self.subTest(obligacion=nombre):
                self.assertEqual(
                    self._estado(centro, nombre),
                    EstadoCumplimiento.NO_APLICA,
                )

    def test_el_piloto_exhibe_los_seis_estados(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")
        nombres = list(ESPERADOS) + list(SIN_RESPALDO) + list(NO_APLICAN)

        observados = {self._estado(centro, nombre) for nombre in nombres}

        self.assertEqual(observados, set(EstadoCumplimiento))

    # --- fidelidad al respaldo --------------------------------------------

    def test_carga_las_fechas_que_declara_la_constancia(self) -> None:
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        evidencia = Evidencia.objects.get(
            centro_costo=centro,
            obligacion=self._obligacion("Manejo de extintores con simulador"),
        )

        # La constancia más antigua del respaldo, que es la que descubre al
        # centro cuando caduca.
        self.assertEqual(evidencia.fecha_emision, date(2024, 4, 8))
        self.assertEqual(evidencia.fecha_vencimiento, date(2027, 4, 8))

    def test_de_cada_obligacion_rige_la_constancia_que_caduca_primero(self) -> None:
        respaldo = leer_resumen()
        self._sembrar()
        centro = CentroCosto.objects.get(codigo_contable="ADM04")

        for curso in respaldo.cursos:
            if not curso.fechadas:
                continue
            with self.subTest(obligacion=curso.nombre):
                evidencia = Evidencia.objects.get(
                    centro_costo=centro,
                    obligacion=self._obligacion(curso.nombre),
                )
                self.assertEqual(
                    evidencia.fecha_emision,
                    min(emision for emision, _ in curso.fechadas),
                )

    def test_sin_carpeta_guarda_un_marcador_que_dice_que_lo_es(self) -> None:
        self._sembrar()

        evidencia = Evidencia.objects.get(
            obligacion=self._obligacion("Manejo de extintores con simulador"),
        )
        with evidencia.archivo.open("rb") as archivo:
            contenido = archivo.read()

        self.assertTrue(contenido.startswith(b"%PDF-"))
        self.assertIn(b"CONSTANCIA NO ADJUNTA", contenido)

    def test_con_carpeta_guarda_la_constancia_original(self) -> None:
        carpeta = self._carpeta_con_la_constancia_que_rige()

        self._sembrar(carpeta=str(carpeta))

        evidencia = Evidencia.objects.get(
            obligacion=self._obligacion("Manejo de extintores con simulador"),
        )
        with evidencia.archivo.open("rb") as archivo:
            contenido = archivo.read()
        self.assertIn(b"CONSTANCIA ORIGINAL DE PRUEBA", contenido)
        self.assertNotIn(b"CONSTANCIA NO ADJUNTA", contenido)

    def test_el_archivo_guardado_no_lleva_el_rut_en_el_nombre(self) -> None:
        # Los escaneos de la clínica se llaman Informe_<RUT>_<marca de tiempo>.
        # La evidencia es del centro de costo, no de la persona.
        carpeta = self._carpeta_con_la_constancia_que_rige()

        self._sembrar(carpeta=str(carpeta))

        for evidencia in Evidencia.objects.all():
            with self.subTest(evidencia=evidencia.pk):
                self.assertNotRegex(evidencia.archivo.name, r"\d{7,8}-[\dkK]")

    def _carpeta_con_la_constancia_que_rige(self) -> Path:
        """Arma una carpeta cuyo archivo coincide con la que el resumen elige."""
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        raiz = Path(directorio.name)
        destino = (
            raiz
            / "3. Auxiliares de bodegas Nivel operativo"
            / "1. Uso y manejo de extintores"
            / "11111111-1 - Prueba Prueba Una"
            / "Diploma_65940_20260821.pdf"
        )
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(
            marcador_pdf(
                [
                    "CONSTANCIA ORIGINAL DE PRUEBA",
                    "REALIZADO: 08 DE ABRIL DE 2024 - DURACION: 2 HORAS",
                    "CODIGO: ABC ---- FECHA EXPIRACION: 08/04/2027",
                ]
            )
        )
        return raiz

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

    def test_la_periodicidad_queda_declarada_como_no_confirmada(self) -> None:
        self._sembrar()

        for obligacion in Obligacion.objects.all():
            with self.subTest(obligacion=str(obligacion)):
                self.assertIn(
                    "preliminares",
                    obligacion.version_actual.motivo,
                )

    def test_el_resumen_versionado_describe_todo_el_catalogo(self) -> None:
        # Si la carpeta gana un curso que el catálogo no describe, la siembra
        # tiene que detenerse en vez de inventarle una norma.
        faltantes = [
            curso.nombre
            for curso in leer_resumen().cursos
            if curso.nombre not in CATALOGO
        ]

        self.assertEqual(faltantes, [])
