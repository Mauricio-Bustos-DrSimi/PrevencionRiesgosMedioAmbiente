from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse


CLAVE_PRUEBA = "clave-segura-de-prueba"


class CierreSesionTests(TestCase):
    def setUp(self) -> None:
        self.usuario = get_user_model().objects.create_user(
            username="usuario_cierre_sesion",
            password=CLAVE_PRUEBA,
        )
        self.usuario.groups.add(Group.objects.get(name="Prevencionista"))

    def _cliente_con_csrf(self, *, autenticado: bool) -> tuple[Client, str]:
        cliente = Client(enforce_csrf_checks=True)
        if autenticado:
            cliente.force_login(self.usuario)
            respuesta = cliente.get(reverse("inicio"))
        else:
            respuesta = cliente.get(reverse("iniciar_sesion"))
        self.assertEqual(respuesta.status_code, 200)
        return cliente, cliente.cookies["csrftoken"].value

    def test_topbar_muestra_formulario_post_con_csrf_al_usuario_autenticado(
        self,
    ) -> None:
        cliente, _ = self._cliente_con_csrf(autenticado=True)

        respuesta = cliente.get(reverse("inicio"))

        self.assertContains(
            respuesta,
            f'<form class="topbar__logout" method="post" action="{reverse("cerrar_sesion")}">',
        )
        self.assertContains(respuesta, 'name="csrfmiddlewaretoken"')
        self.assertContains(respuesta, ">Cerrar sesión</button>")

    def test_post_valido_invalida_sesion_y_redirige_al_acceso(self) -> None:
        cliente, token = self._cliente_con_csrf(autenticado=True)

        respuesta = cliente.post(
            reverse("cerrar_sesion"),
            {"csrfmiddlewaretoken": token},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertRedirects(
            respuesta,
            reverse("iniciar_sesion"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", cliente.session)
        protegida = cliente.get(reverse("inicio"))
        self.assertRedirects(
            protegida,
            f'{reverse("iniciar_sesion")}?next={reverse("inicio")}',
            fetch_redirect_response=False,
        )

    def test_post_sin_csrf_es_rechazado_y_conserva_la_sesion(self) -> None:
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)

        respuesta = cliente.post(reverse("cerrar_sesion"))

        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("_auth_user_id", cliente.session)

    def test_get_no_cierra_la_sesion(self) -> None:
        cliente = Client()
        cliente.force_login(self.usuario)

        respuesta = cliente.get(reverse("cerrar_sesion"))

        self.assertEqual(respuesta.status_code, 405)
        self.assertIn("_auth_user_id", cliente.session)

    def test_usuario_anonimo_puede_enviar_post_valido_sin_error(self) -> None:
        cliente, token = self._cliente_con_csrf(autenticado=False)

        respuesta = cliente.post(
            reverse("cerrar_sesion"),
            {"csrfmiddlewaretoken": token},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertRedirects(
            respuesta,
            reverse("iniciar_sesion"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", cliente.session)
