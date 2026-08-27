from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TipoVersion, VersionObligacion


class PlanAplicacionHttpTests(TestCase):
    def setUp(self) -> None:
        grupo = Group.objects.get(name="Prevencionista")
        self.usuario = get_user_model().objects.create_user(
            username="prevencionista_plan",
            password="clave-segura-de-prueba",
        )
        self.usuario.groups.add(grupo)
        self.centro = CentroCosto.objects.create(
            codigo_contable="FAR-PLAN-001",
            nombre="Farmacia Plan",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        self.otro_centro = CentroCosto.objects.create(
            codigo_contable="BOD-PLAN-001",
            nombre="Bodega Plan",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Mantener extintores certificados",
            norma_origen="DS 594",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.usuario,
            motivo="Alta de prueba",
        )
        self.client.force_login(self.usuario)

    def test_sugerencia_se_confirma_solo_para_el_centro_seleccionado(self) -> None:
        respuesta = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.centro.pk]),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sugerencia inicial para Farmacia")
        self.assertContains(respuesta, "Mantener extintores certificados")

        confirmar = self.client.post(
            reverse("planes_aplicacion:confirmar_sugerencia", args=[self.centro.pk]),
            {"motivo": "Configuración inicial del piloto"},
        )

        self.assertRedirects(
            confirmar,
            reverse("planes_aplicacion:plan", args=[self.centro.pk]),
        )
        plan = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.centro.pk]),
        )
        otro_plan = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.otro_centro.pk]),
        )
        self.assertContains(plan, "Sin evidencia")
        self.assertContains(plan, "Configuración inicial del piloto")
        self.assertContains(otro_plan, "Sugerencia inicial")
        self.assertContains(otro_plan, "Confirmar plan sugerido")

    def test_agregar_y_declarar_no_aplica_exigen_motivo_y_distinguen_estado(
        self,
    ) -> None:
        url = reverse("planes_aplicacion:plan", args=[self.centro.pk])
        respuesta_sin_motivo = self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {"obligacion": str(self.obligacion.pk), "motivo": ""},
        )
        self.assertEqual(respuesta_sin_motivo.status_code, 200)
        self.assertContains(respuesta_sin_motivo, "Este campo es obligatorio")

        agregado = self.client.post(
            reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "Aplica a esta instalación",
            },
        )
        self.assertRedirects(agregado, url)
        self.assertContains(self.client.get(url), "Sin evidencia")

        no_aplica = self.client.post(
            reverse("planes_aplicacion:no_aplica", args=[self.centro.pk]),
            {
                "obligacion": str(self.obligacion.pk),
                "motivo": "No corresponde por el proceso local",
            },
        )
        self.assertRedirects(no_aplica, url)
        plan = self.client.get(url)
        self.assertContains(plan, "No aplica")
        self.assertNotContains(plan, "Sin evidencia")

    def test_plan_se_puede_reconstruir_a_una_fecha_pasada(self) -> None:
        url = reverse("planes_aplicacion:plan", args=[self.centro.pk])
        with patch(
            "django.utils.timezone.now",
            return_value=timezone.make_aware(datetime(2026, 8, 25, 10, 0)),
        ):
            self.client.post(
                reverse("planes_aplicacion:agregar", args=[self.centro.pk]),
                {
                    "obligacion": str(self.obligacion.pk),
                    "motivo": "Aplicación inicial",
                },
            )
        with patch(
            "django.utils.timezone.now",
            return_value=timezone.make_aware(datetime(2026, 8, 26, 10, 0)),
        ):
            self.client.post(
                reverse("planes_aplicacion:no_aplica", args=[self.centro.pk]),
                {
                    "obligacion": str(self.obligacion.pk),
                    "motivo": "Cambio documentado",
                },
            )

        pasado = self.client.get(f"{url}?fecha=2026-08-25")

        self.assertEqual(pasado.status_code, 200)
        self.assertContains(pasado, "Consulta histórica al 25/08/2026")
        self.assertContains(pasado, "Sin evidencia")
        self.assertNotContains(pasado, "No aplica")

    def test_usuario_sin_rol_no_puede_configurar_plan(self) -> None:
        usuario = get_user_model().objects.create_user(username="sin_rol_plan")
        self.client.force_login(usuario)

        respuesta = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.centro.pk]),
        )

        self.assertEqual(respuesta.status_code, 403)
