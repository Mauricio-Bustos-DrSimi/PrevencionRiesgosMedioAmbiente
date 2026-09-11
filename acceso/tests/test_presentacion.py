from django.test import SimpleTestCase

from acceso.templatetags.presentacion import rut_oculto


class PresentacionTests(SimpleTestCase):
    def test_oculta_el_rut_normal_y_con_digito_k(self) -> None:
        self.assertEqual(rut_oculto("12345678-5"), "••.•••.678-5")
        self.assertEqual(rut_oculto("12.345.670-k"), "••.•••.670-K")

    def test_un_identificador_corto_no_expone_todo_su_cuerpo(self) -> None:
        oculto = rut_oculto("12-K")

        self.assertEqual(oculto, "••.•••.•••-K")
        self.assertNotIn("12", oculto)
