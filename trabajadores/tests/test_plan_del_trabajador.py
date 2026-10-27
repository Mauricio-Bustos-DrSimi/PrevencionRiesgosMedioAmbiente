"""El cargo sugiere; la persona confirma. Y lo no validado no acredita.

La sugerencia por cargo es lo que evita armar el plan de 129 personas
obligación por obligación, pero no puede decidir por ellas: la aplicabilidad
se confirma individualmente y no se mueve sola cuando alguien cambia de cargo.
"""

import tempfile
from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aceptacion.reloj import reloj_en
from centros_costo.models import CentroCosto
from evidencias.services import (
    EstadoCumplimiento,
    cargar_evidencia,
    caso_de_cumplimiento,
    caso_de_trabajador,
)
from importaciones.lectura_constancias import leer_resumen
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad
from planes_aplicacion.services import (
    estado_actual_trabajador,
    obligaciones_sugeridas,
    obligaciones_sugeridas_trabajador,
)
from trabajadores.models import AsignacionTrabajador, TipoAsignacion, Trabajador
from trabajadores.models import ValidacionTrabajador
from trabajadores.rut import digito_verificador


EN_FECHA = date(2026, 9, 1)

CONDUCTOR = "Operadores de maquinaria (Nivel ope)"
ASEO = "Auxiliar de aseo(Nivel opera)"


class SugerenciaPorCargoTests(TestCase):
    def setUp(self) -> None:
        # El plan y la dotación se crean antes del corte histórico consultado.
        self.enterContext(
            reloj_en(timezone.make_aware(datetime.combine(EN_FECHA, time(12))))
        )
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        override = self.settings(MEDIA_ROOT=directorio.name)
        override.enable()
        self.addCleanup(override.disable)
        self.actor: User = get_user_model().objects.create_user(username="prevencion")
        self.actor.groups.add(Group.objects.get(name="Prevencionista"))
        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM-CARGOS",
            nombre="Bodega de cargos",
            tipo=CentroCosto.Tipo.BODEGA,
        )

    def _obligacion(
        self,
        nombre: str,
        *,
        titular: str = TitularObligacion.TRABAJADOR,
        cargos: list[str] | None = None,
    ) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=nombre,
            norma_origen="Norma de prueba",
            titular=titular,
            periodicidad="anual",
            tipos_centro=[],
            cargos_sugeridos=cargos or [],
            tipo_version=TipoVersion.ALTA,
            autor=self.actor,
            motivo="Alta de prueba.",
        )
        return obligacion

    def _rut(self, numero: int) -> str:
        cuerpo = str(10000000 + numero)
        return f"{cuerpo}-{digito_verificador(cuerpo)}"

    def _trabajador(self, rut: str, cargo: str, *, validado: bool = True) -> Trabajador:
        trabajador = Trabajador.objects.create(
            rut=rut,
            nombre=f"Persona {rut}",
            cargo=cargo,
            creado_por=self.actor,
        )
        AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=self.centro,
            tipo=TipoAsignacion.ALTA,
            motivo="Alta de prueba.",
            autor=self.actor,
        )
        if validado:
            ValidacionTrabajador.objects.create(
                trabajador=trabajador,
                validado_por=self.actor,
            )
        return trabajador

    def _confirmar(self, trabajador: Trabajador, obligacion: Obligacion) -> None:
        CambioAplicabilidad.objects.create(
            trabajador=trabajador,
            obligacion=obligacion,
            aplica=True,
            motivo="Confirmado individualmente.",
            autor=self.actor,
        )

    def test_administrador_conserva_todas_las_acciones_de_dotacion(self) -> None:
        trabajador = self._trabajador(
            "11111111-1",
            CONDUCTOR,
            validado=False,
        )
        sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_dotacion",
            password="clave-segura-de-prueba",
        )
        self.client.force_login(sysadmin)

        detalle = self.client.get(
            reverse("trabajadores:detalle", args=[trabajador.pk]),
        )

        self.assertEqual(detalle.status_code, 200)
        self.assertContains(
            detalle,
            reverse("trabajadores:validar", args=[trabajador.pk]),
        )
        self.assertContains(
            detalle,
            reverse("trabajadores:trasladar", args=[trabajador.pk]),
        )
        self.assertContains(
            detalle,
            reverse("trabajadores:dar_de_baja", args=[trabajador.pk]),
        )

    # --- la sugerencia ----------------------------------------------------

    def test_los_seis_cargos_del_respaldo_reciben_su_sugerencia(self) -> None:
        """Los seis niveles de carpeta de ADM04, con lo que cada uno acredita.

        La sugerencia sale del propio respaldo: cada curso se propone a los
        cargos que aparecen con constancias suyas, y a ningún otro.
        """
        respaldo = leer_resumen()
        cargos = sorted({grupo for curso in respaldo.cursos for grupo in curso.grupos})
        self.assertEqual(len(cargos), 6)

        for curso in respaldo.cursos:
            self._obligacion(curso.nombre, cargos=sorted(curso.grupos))

        for numero, cargo in enumerate(cargos):
            with self.subTest(cargo=cargo):
                trabajador = self._trabajador(self._rut(numero), cargo)
                sugeridas = {
                    obligacion.version_actual.nombre
                    for obligacion in obligaciones_sugeridas_trabajador(trabajador)
                }
                esperadas = {
                    curso.nombre
                    for curso in respaldo.cursos
                    if cargo in curso.grupos
                }
                self.assertEqual(sugeridas, esperadas)
                self.assertNotEqual(sugeridas, set())

    def test_la_sugerencia_del_centro_conserva_su_filtro_por_titular(self) -> None:
        del_centro = self._obligacion(
            "Matriz IPER vigente",
            titular=TitularObligacion.CENTRO_COSTO,
        )
        self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])

        sugeridas = obligaciones_sugeridas(self.centro)

        self.assertEqual([obligacion.pk for obligacion in sugeridas], [del_centro.pk])

    def test_un_cargo_sin_obligaciones_no_recibe_ninguna(self) -> None:
        self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        aseo = self._trabajador("11111111-1", ASEO)

        self.assertEqual(obligaciones_sugeridas_trabajador(aseo), [])

    def test_una_obligacion_sin_cargos_se_sugiere_a_todos(self) -> None:
        # Vacío significa todos, igual que en los tipos de centro.
        self._obligacion("Orientación en prevención de riesgos", cargos=[])
        aseo = self._trabajador("11111111-1", ASEO)

        self.assertEqual(len(obligaciones_sugeridas_trabajador(aseo)), 1)

    # --- la confirmación individual ---------------------------------------

    def test_cambiar_el_cargo_no_modifica_el_plan_ya_confirmado(self) -> None:
        licencia = self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        trabajador = self._trabajador("11111111-1", CONDUCTOR)
        self._confirmar(trabajador, licencia)
        cambios_antes = CambioAplicabilidad.objects.count()

        trabajador.cargo = ASEO
        trabajador.save()

        # El cargo dejó de sugerirla, pero lo que Prevención confirmó sigue
        # confirmado: la aplicabilidad no se hereda ni se pierde sola.
        self.assertEqual(obligaciones_sugeridas_trabajador(trabajador), [])
        self.assertEqual(CambioAplicabilidad.objects.count(), cambios_antes)
        cambio = estado_actual_trabajador(trabajador, licencia)
        assert cambio is not None
        self.assertTrue(cambio.aplica)

    def test_una_obligacion_excluida_del_plan_produce_no_aplica(self) -> None:
        licencia = self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        trabajador = self._trabajador("11111111-1", CONDUCTOR)
        CambioAplicabilidad.objects.create(
            trabajador=trabajador,
            obligacion=licencia,
            aplica=False,
            motivo="No conduce vehículos de la empresa.",
            autor=self.actor,
        )

        caso = caso_de_trabajador(
            trabajador=trabajador,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )

        assert caso is not None
        self.assertEqual(caso.estado, EstadoCumplimiento.NO_APLICA)

    # --- lo que no acredita -----------------------------------------------

    def test_un_trabajador_no_validado_no_produce_cumplimiento(self) -> None:
        licencia = self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        trabajador = self._trabajador("11111111-1", CONDUCTOR, validado=False)
        self._confirmar(trabajador, licencia)
        # Su documento existe y sería Vigente si la persona estuviera
        # incorporada: lo que no acredita es la persona, no el papel.
        cargar_evidencia(
            centro=self.centro,
            obligacion=licencia,
            actor=self.actor,
            archivo=SimpleUploadedFile(
                "licencia.pdf",
                b"Licencia de conducir de prueba",
                content_type="application/pdf",
            ),
            emisor="Municipalidad",
            fecha_emision=date(2026, 8, 1),
            fecha_vencimiento=date(2027, 8, 1),
            trabajador=trabajador,
        )

        caso = caso_de_trabajador(
            trabajador=trabajador,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )
        agregado = caso_de_cumplimiento(
            centro=self.centro,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )

        assert caso is not None
        self.assertEqual(caso.estado, EstadoCumplimiento.PENDIENTE_VALIDACION)
        # La dotación del centro no crece porque alguien haya creado una ficha.
        assert agregado is not None
        self.assertEqual(agregado.estado, EstadoCumplimiento.NO_APLICA)
        self.assertEqual(agregado.trabajadores_aplicables, 0)

    def test_un_centro_sin_trabajadores_aplicables_resulta_no_aplica(self) -> None:
        licencia = self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        self._trabajador("11111111-1", CONDUCTOR)

        agregado = caso_de_cumplimiento(
            centro=self.centro,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )

        assert agregado is not None
        self.assertEqual(agregado.estado, EstadoCumplimiento.NO_APLICA)
        self.assertEqual(agregado.trabajadores_aplicables, 0)

    def test_un_trabajador_dado_de_baja_deja_de_exigirse(self) -> None:
        licencia = self._obligacion("Licencia de conducir", cargos=[CONDUCTOR])
        trabajador = self._trabajador("11111111-1", CONDUCTOR)
        self._confirmar(trabajador, licencia)
        AsignacionTrabajador.objects.create(
            trabajador=trabajador,
            centro_costo=None,
            tipo=TipoAsignacion.BAJA,
            motivo="Egresa de la empresa.",
            autor=self.actor,
        )

        caso = caso_de_trabajador(
            trabajador=trabajador,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )
        agregado = caso_de_cumplimiento(
            centro=self.centro,
            obligacion=licencia,
            en_fecha=EN_FECHA,
        )

        self.assertIsNone(caso)
        assert agregado is not None
        self.assertEqual(agregado.estado, EstadoCumplimiento.NO_APLICA)
