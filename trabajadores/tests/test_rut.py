"""El RUT es la identidad del trabajador: reconocerlo es lógica pura.

No necesita HTTP. Lo que estas pruebas resguardan es que las escrituras que
aparecen en la carpeta de respaldo —con puntos, sin puntos, con el dígito
verificador en minúscula, con espacios— identifiquen a una sola persona, y que
un RUT inventado no cree una segunda.
"""

from django.test import SimpleTestCase

from trabajadores.rut import RutInvalido, digito_verificador, normalizar_rut


class NormalizacionRutTests(SimpleTestCase):
    def test_la_forma_canonica_no_lleva_puntos_y_si_guion(self) -> None:
        self.assertEqual(normalizar_rut("12.345.678-5"), "12345678-5")

    def test_las_escrituras_del_respaldo_son_la_misma_persona(self) -> None:
        escrituras = [
            "12.345.678-5",
            "12345678-5",
            "123456785",
            " 12.345.678 - 5 ",
        ]

        canonicos = {normalizar_rut(escritura) for escritura in escrituras}

        self.assertEqual(canonicos, {"12345678-5"})

    def test_el_digito_verificador_k_se_guarda_en_mayuscula(self) -> None:
        self.assertEqual(normalizar_rut("12.345.670-k"), "12345670-K")

    def test_los_ceros_a_la_izquierda_no_crean_otra_persona(self) -> None:
        self.assertEqual(normalizar_rut("012.345.678-5"), "12345678-5")

    def test_un_digito_verificador_incorrecto_se_rechaza(self) -> None:
        with self.assertRaises(RutInvalido) as fallo:
            normalizar_rut("12.345.678-9")

        self.assertIn("verificador", str(fallo.exception))
        self.assertIn("5", str(fallo.exception))

    def test_un_rut_mal_formado_se_rechaza(self) -> None:
        for escritura in ("", "sin rut", "12345-6789-0", "abc-1", "1234-5"):
            with self.subTest(escritura=escritura):
                with self.assertRaises(RutInvalido):
                    normalizar_rut(escritura)

    def test_el_digito_verificador_se_calcula_por_modulo_once(self) -> None:
        # Los dos casos que el módulo 11 resuelve de forma especial —resto 10
        # es K, resto 11 es 0— más dos corrientes.
        self.assertEqual(digito_verificador("12345678"), "5")
        self.assertEqual(digito_verificador("12345670"), "K")
        self.assertEqual(digito_verificador("11111111"), "1")
        self.assertEqual(digito_verificador("10000004"), "0")
