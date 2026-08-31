"""La lectura de la carpeta de respaldo interpreta lo que las constancias dicen."""

import tempfile
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from importaciones.lectura_constancias import (
    CarpetaIlegible,
    fechas_de_constancia,
    leer_carpeta,
    nombre_de_obligacion,
    resumir,
)
from importaciones.pdf import marcador_pdf, texto_de_pdf


# El texto que dibujan las constancias de la plataforma, tal como aparece.
CONSTANCIA = [
    "USO Y MANEJO DE EXTINTORES",
    "NOMBRE DE PRUEBA UNO",
    "FARMACIAS DE SIMILARES CHILE S.A.",
    "REALIZADO: 08 DE ABRIL DE 2024 - DURACION: 2 HORAS",
    "CODIGO: 8B494FDED41241E1B373EC070B57593E ---- FECHA EXPIRACION: 08/04/2027",
]


class TextoDePdfTests(SimpleTestCase):
    def test_lee_el_texto_que_el_pdf_dibuja(self) -> None:
        texto = texto_de_pdf(marcador_pdf(CONSTANCIA))

        self.assertIn("USO Y MANEJO DE EXTINTORES", texto)
        self.assertIn("REALIZADO: 08 DE ABRIL DE 2024", texto)

    def test_un_pdf_sin_capa_de_texto_no_inventa_nada(self) -> None:
        # Los exámenes ocupacionales son escaneos: la página es una imagen y no
        # hay operadores de texto que leer.
        self.assertEqual(texto_de_pdf(b"%PDF-1.4\n%%EOF\n"), "")


class FechasDeConstanciaTests(SimpleTestCase):
    def test_lee_la_realizacion_y_la_expiracion(self) -> None:
        emision, vencimiento = fechas_de_constancia(texto_de_pdf(marcador_pdf(CONSTANCIA)))

        self.assertEqual(emision, date(2024, 4, 8))
        self.assertEqual(vencimiento, date(2027, 4, 8))

    def test_acepta_el_mes_con_tilde(self) -> None:
        emision, _ = fechas_de_constancia("REALIZADO: 03 DE DICIEMBRE DE 2024")

        self.assertEqual(emision, date(2024, 12, 3))

    def test_sin_texto_no_hay_fechas(self) -> None:
        self.assertEqual(fechas_de_constancia(""), (None, None))

    def test_descarta_el_par_incoherente(self) -> None:
        # Si la expiración precede a la realización, el par no se puede creer y
        # la constancia queda para que Prevención la revise a mano.
        emision, vencimiento = fechas_de_constancia(
            "REALIZADO: 08 DE ABRIL DE 2024 FECHA EXPIRACION: 08/04/2023"
        )

        self.assertIsNone(emision)
        self.assertIsNone(vencimiento)


class NombreDeObligacionTests(SimpleTestCase):
    def test_reune_las_variantes_de_escritura_de_un_mismo_curso(self) -> None:
        # La carpeta escribe el curso de seis maneras y lo numera distinto en
        # cada grupo de cargo; todas son la misma obligación.
        variantes = [
            "1. Fortaleciendo competencias Psicosociales Jefaturas",
            "2. Fortaleciendo Competencias psicosociales",
            "2. Fortaleciendo comp psico",
            "1. Fortaleciendo competencias psico",
        ]

        nombres = {nombre_de_obligacion(variante, "") for variante in variantes}

        self.assertEqual(nombres, {"Fortalecimiento de competencias psicosociales"})

    def test_las_dos_carpetas_de_extintores_son_el_mismo_curso(self) -> None:
        # La carpeta los separa, pero las 101 constancias de una y de otra
        # llevan impreso el mismo título: es un solo curso archivado dos veces.
        self.assertEqual(
            nombre_de_obligacion("1. Uso y manejo de extintores", ""),
            nombre_de_obligacion("2. Manejo de extintores con simulador", ""),
        )

    def test_el_examen_ocupacional_se_separa_por_subtipo(self) -> None:
        self.assertEqual(
            nombre_de_obligacion("3. Examenes Ocupacionales", "1. Altura Fisica"),
            "Examen ocupacional de altura física",
        )
        self.assertEqual(
            nombre_de_obligacion("2. Examenes ocupacionales", "2. Conductor clase D"),
            "Examen ocupacional de conductor clase D",
        )

    def test_una_carpeta_desconocida_no_se_adivina(self) -> None:
        self.assertIsNone(nombre_de_obligacion("9. Curso que no existe", ""))


class LeerCarpetaTests(SimpleTestCase):
    def setUp(self) -> None:
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.raiz = Path(directorio.name)

    def _constancia(self, ruta: str, lineas: list[str]) -> None:
        destino = self.raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(marcador_pdf(lineas))

    def test_interpreta_la_estructura_de_carpetas(self) -> None:
        self._constancia(
            "1. Jefaturas de bodegas/2. Manejo de extintores con simulador/"
            "11111111-1 - Prueba Prueba Una/Diploma_65940_20260824.pdf",
            CONSTANCIA,
        )
        self._constancia(
            "3. Auxiliares de bodegas Nivel operativo/3. Examenes Ocupacionales/"
            "1. Altura Fisica/22222222-2 - Prueba Prueba Dos/Informe.pdf",
            ["ESCANEO SIN FECHA"],
        )

        constancias = leer_carpeta(self.raiz)

        self.assertEqual(len(constancias), 2)
        por_nombre = {c.obligacion: c for c in constancias}
        self.assertEqual(
            set(por_nombre),
            {
                "Manejo de extintores con simulador",
                "Examen ocupacional de altura física",
            },
        )
        con_simulador = por_nombre["Manejo de extintores con simulador"]
        self.assertEqual(con_simulador.fecha_emision, date(2024, 4, 8))
        self.assertEqual(con_simulador.grupo, "Jefaturas de bodegas")
        self.assertFalse(por_nombre["Examen ocupacional de altura física"].esta_fechada)

    def test_una_carpeta_que_no_existe_se_dice_en_vez_de_devolver_vacio(self) -> None:
        with self.assertRaises(CarpetaIlegible):
            leer_carpeta(self.raiz / "no-existe")

    def test_el_resumen_no_conserva_nombres_ni_rut(self) -> None:
        self._constancia(
            "1. Jefaturas de bodegas/1. Uso y manejo de extintores/"
            "11111111-1 - Prueba Prueba Una/Diploma_65940_20260824.pdf",
            CONSTANCIA,
        )
        self._constancia(
            "1. Jefaturas de bodegas/1. Uso y manejo de extintores/"
            "22222222-2 - Prueba Prueba Dos/Diploma_65940_20260825.pdf",
            CONSTANCIA,
        )

        respaldo = resumir(
            leer_carpeta(self.raiz),
            codigo_contable="ADM04",
            nombre="Bodega de Distribución",
            tipo="bodega",
        )

        self.assertEqual(respaldo.trabajadores_distintos, 2)
        self.assertEqual(respaldo.constancias_totales, 2)
        rendido = repr(respaldo)
        self.assertNotIn("11111111", rendido)
        self.assertNotIn("Prueba Prueba Una", rendido)

    def test_cuenta_a_la_persona_una_sola_vez_pese_a_como_se_escriba(self) -> None:
        # La carpeta escribe el mismo RUT con separadores distintos y con el
        # nombre truncado. El RUT es la única llave confiable.
        self._constancia(
            "1. Jefaturas de bodegas/1. Uso y manejo de extintores/"
            "33333333-3 -Prueba Prueba Tres Nombre Completo/a.pdf",
            CONSTANCIA,
        )
        self._constancia(
            "1. Jefaturas de bodegas/3. Orientación en prevención de riesgos "
            "Laborales/33333333-3 - Prueba Prueba Tres/b.pdf",
            CONSTANCIA,
        )

        respaldo = resumir(
            leer_carpeta(self.raiz),
            codigo_contable="ADM04",
            nombre="Bodega de Distribución",
            tipo="bodega",
        )

        self.assertEqual(respaldo.trabajadores_distintos, 1)
        self.assertEqual(respaldo.constancias_totales, 2)
