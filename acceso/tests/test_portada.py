from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class PortadaProtegidaTests(TestCase):
    def test_usuario_sin_sesion_es_redirigido_al_inicio_de_sesion(self) -> None:
        respuesta = self.client.get("/")

        self.assertRedirects(
            respuesta,
            "/cuentas/iniciar-sesion/?next=/",
            fetch_redirect_response=False,
        )

    def test_usuario_sin_rol_no_puede_abrir_la_portada(self) -> None:
        usuario = get_user_model().objects.create_user(
            username="sin_rol",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(usuario)

        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 403)

    def test_prevencionista_inicia_sesion_y_abre_la_portada(self) -> None:
        grupo = Group.objects.get(name="Prevencionista")
        usuario = get_user_model().objects.create_user(
            username="prevencionista",
            password="clave-segura-de-prueba",
        )
        usuario.groups.add(grupo)

        respuesta_login = self.client.post(
            "/cuentas/iniciar-sesion/",
            {
                "username": "prevencionista",
                "password": "clave-segura-de-prueba",
            },
        )
        respuesta_portada = self.client.get("/")

        self.assertRedirects(
            respuesta_login,
            "/",
            fetch_redirect_response=False,
        )
        self.assertEqual(respuesta_portada.status_code, 200)
        self.assertTemplateUsed(respuesta_portada, "acceso/inicio.html")
        self.assertContains(respuesta_portada, "prevencionista")
        self.assertContains(
            respuesta_portada,
            reverse("evidencias:vencimientos"),
        )
        self.assertContains(
            respuesta_portada,
            reverse("evidencias:pendientes"),
        )

    def test_sysadmin_crea_cuenta_y_asigna_el_grupo_prevencionista(self) -> None:
        sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)

        respuesta_crear = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "cuenta_piloto",
                "password1": "clave-segura-de-prueba",
                "password2": "clave-segura-de-prueba",
                "_save": "Guardar",
            },
        )
        usuario = get_user_model().objects.get(username="cuenta_piloto")
        grupo = Group.objects.get(name="Prevencionista")
        fecha_alta = timezone.localtime(usuario.date_joined)
        respuesta_asignar = self.client.post(
            reverse("admin:auth_user_change", args=[usuario.pk]),
            {
                "username": usuario.username,
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "groups": [str(grupo.pk)],
                "date_joined_0": fecha_alta.strftime("%d/%m/%Y"),
                "date_joined_1": fecha_alta.strftime("%H:%M:%S"),
                "_save": "Guardar",
            },
        )
        respuesta_bitacora = self.client.get(
            reverse("admin:bitacora_eventobitacora_changelist"),
        )
        self.assertContains(respuesta_bitacora, "Cuenta local")
        self.assertContains(respuesta_bitacora, "cuenta_piloto")
        self.assertContains(respuesta_bitacora, "Prevencionista")
        self.assertContains(respuesta_bitacora, "sysadmin")
        self.assertContains(respuesta_bitacora, "Panel administrativo")
        self.client.logout()
        respuesta_login = self.client.post(
            "/cuentas/iniciar-sesion/",
            {
                "username": "cuenta_piloto",
                "password": "clave-segura-de-prueba",
            },
        )
        respuesta_portada = self.client.get("/")

        self.assertEqual(respuesta_crear.status_code, 302)
        self.assertEqual(respuesta_asignar.status_code, 302)
        self.assertRedirects(
            respuesta_login,
            "/",
            fetch_redirect_response=False,
        )
        self.assertEqual(respuesta_portada.status_code, 200)
        self.assertContains(respuesta_portada, "cuenta_piloto")
