from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from acceso.models import AsignacionEncargadoCentro, TipoAsignacionEncargado
from acceso.permisos import centros_visibles_para
from centros_costo.models import CentroCosto
from trabajadores.models import AsignacionTrabajador, TipoAsignacion, Trabajador


class PermisosPorCentroTests(TestCase):
    def setUp(self) -> None:
        self.grupo_encargado = Group.objects.get(name="Encargado")
        self.grupo_prevencionista = Group.objects.get(name="Prevencionista")
        self.administrador = get_user_model().objects.create_superuser(
            username="administrador_mvp",
            password="clave-ficticia",
        )
        self.prevencionista = self._usuario("prevencionista_mvp")
        self.prevencionista.groups.add(self.grupo_prevencionista)
        self.encargado = self._usuario("encargado_mvp")
        self.encargado.groups.add(self.grupo_encargado)
        self.centro_asignado = CentroCosto.objects.create(
            codigo_contable="CENTRO-FICTICIO-A",
            nombre="Centro ficticio asignado",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.otro_centro = CentroCosto.objects.create(
            codigo_contable="CENTRO-FICTICIO-B",
            nombre="Centro ficticio no asignado",
            tipo=CentroCosto.Tipo.FARMACIA,
        )
        AsignacionEncargadoCentro.objects.create(
            usuario=self.encargado,
            centro_costo=self.centro_asignado,
            tipo=TipoAsignacionEncargado.ASIGNACION,
            motivo="Asignación ficticia para prueba",
            autor=self.administrador,
        )
        self.trabajador_asignado = self._trabajador(
            "11111111-1", "Persona Ficticia A", self.centro_asignado
        )
        self.otro_trabajador = self._trabajador(
            "22222222-2", "Persona Ficticia B", self.otro_centro
        )

    @staticmethod
    def _usuario(nombre: str) -> User:
        return get_user_model().objects.create_user(
            username=nombre,
            password="clave-ficticia",
        )

    def _trabajador(self, rut: str, nombre: str, centro: CentroCosto) -> Trabajador:
        trabajador = Trabajador.objects.create(
            rut=rut,
            nombre=nombre,
            cargo="Cargo ficticio",
            creado_por=self.prevencionista,
        )
        AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=centro,
            tipo=TipoAsignacion.ALTA,
            motivo="Alta ficticia",
            autor=self.prevencionista,
        )
        return trabajador

    def test_encargado_solo_consulta_su_centro_y_no_puede_cambiar_id(self) -> None:
        self.client.force_login(self.encargado)

        listado = self.client.get(reverse("centros_costo:lista"))
        propio = self.client.get(
            reverse("centros_costo:detalle", args=[self.centro_asignado.pk])
        )
        ajeno = self.client.get(
            reverse("centros_costo:detalle", args=[self.otro_centro.pk])
        )
        trabajador_propio = self.client.get(
            reverse("trabajadores:detalle", args=[self.trabajador_asignado.pk])
        )
        trabajador_ajeno = self.client.get(
            reverse("trabajadores:detalle", args=[self.otro_trabajador.pk])
        )
        plan_propio = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.centro_asignado.pk])
        )
        plan_ajeno = self.client.get(
            reverse("planes_aplicacion:plan", args=[self.otro_centro.pk])
        )

        self.assertEqual(propio.status_code, 200)
        self.assertEqual(trabajador_propio.status_code, 200)
        self.assertEqual(plan_propio.status_code, 200)
        self.assertEqual(ajeno.status_code, 403)
        self.assertEqual(trabajador_ajeno.status_code, 403)
        self.assertEqual(plan_ajeno.status_code, 403)
        self.assertContains(listado, self.centro_asignado.nombre)
        self.assertNotContains(listado, self.otro_centro.nombre)
        self.assertNotContains(listado, self.otro_trabajador.nombre)

    def test_encargado_ve_operacion_pero_no_acciones_de_escritura(self) -> None:
        self.client.force_login(self.encargado)

        for nombre in ("inicio", "evidencias:operacion", "evidencias:vencimientos"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        for url in (
            reverse("trabajadores:crear"),
            reverse("trabajadores:validar", args=[self.trabajador_asignado.pk]),
            reverse("trabajadores:trasladar", args=[self.trabajador_asignado.pk]),
            reverse("trabajadores:dar_de_baja", args=[self.trabajador_asignado.pk]),
            reverse("planes_aplicacion:agregar", args=[self.centro_asignado.pk]),
            reverse("evidencias:pendientes"),
            reverse("importaciones:importar"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

        pagina = self.client.get(reverse("centros_costo:lista"))
        self.assertContains(pagina, "Encargado")
        self.assertNotContains(pagina, reverse("evidencias:pendientes"))
        self.assertNotContains(pagina, reverse("importaciones:importar"))
        self.assertNotContains(pagina, reverse("admin:index"))

    def test_prevencionista_y_administrador_conservan_alcance_global(self) -> None:
        for usuario in (self.prevencionista, self.administrador):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                listado = self.client.get(reverse("centros_costo:lista"))
                self.assertContains(listado, self.centro_asignado.nombre)
                self.assertContains(listado, self.otro_centro.nombre)
                self.assertEqual(
                    self.client.get(reverse("trabajadores:crear")).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.get(reverse("importaciones:importar")).status_code,
                    200,
                )

    def test_solo_administrador_gestiona_asignaciones_desde_admin(self) -> None:
        url = reverse("admin:acceso_asignacionencargadocentro_add")
        self.client.force_login(self.prevencionista)
        self.assertEqual(self.client.get(url).status_code, 302)

        otro_encargado = self._usuario("otro_encargado_mvp")
        otro_encargado.groups.add(self.grupo_encargado)
        self.client.force_login(self.administrador)
        respuesta = self.client.post(
            url,
            {
                "usuario": otro_encargado.pk,
                "centro_costo": self.otro_centro.pk,
                "tipo": TipoAsignacionEncargado.ASIGNACION,
                "motivo": "Asignación ficticia desde administración",
                "_save": "Guardar",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            AsignacionEncargadoCentro.objects.filter(
                usuario=otro_encargado,
                centro_costo=self.otro_centro,
                autor=self.administrador,
            ).exists()
        )

    def test_revocacion_cierra_acceso_sin_borrar_historial(self) -> None:
        AsignacionEncargadoCentro.objects.create(
            usuario=self.encargado,
            centro_costo=self.centro_asignado,
            tipo=TipoAsignacionEncargado.REVOCACION,
            motivo="Revocación ficticia",
            autor=self.administrador,
        )

        self.assertFalse(
            centros_visibles_para(self.encargado).filter(pk=self.centro_asignado.pk).exists()
        )
        self.assertEqual(
            AsignacionEncargadoCentro.objects.filter(
                usuario=self.encargado,
                centro_costo=self.centro_asignado,
            ).count(),
            2,
        )
        with self.assertRaises(ValidationError):
            AsignacionEncargadoCentro.objects.filter(usuario=self.encargado).delete()
