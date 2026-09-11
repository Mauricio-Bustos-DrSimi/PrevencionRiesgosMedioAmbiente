"""La bandeja no puede degradarse al enumerar por persona.

El respaldo del piloto son 129 trabajadores por 14 obligaciones: si resolver
cada caso cuesta una consulta, pintar la bandeja cuesta miles. Lo que se
comprueba aquí no es un tiempo —que depende de la máquina— sino que **el
número de consultas no crece con la dotación**.
"""

from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from aceptacion.reloj import reloj_en
from centros_costo.models import CentroCosto
from evidencias.services import caso_de_cumplimiento, casos_de_cumplimiento
from obligaciones.models import (
    Obligacion,
    TipoVersion,
    TitularObligacion,
    VersionObligacion,
)
from planes_aplicacion.models import CambioAplicabilidad
from trabajadores.models import AsignacionTrabajador, TipoAsignacion, Trabajador
from trabajadores.models import ValidacionTrabajador
from trabajadores.rut import digito_verificador


EN_FECHA = date(2026, 9, 1)


class EscalaDeLasBandejasTests(TestCase):
    def setUp(self) -> None:
        # Las altas deben existir en la fecha que consulta cada prueba.
        self.enterContext(
            reloj_en(timezone.make_aware(datetime.combine(EN_FECHA, time(12))))
        )
        self.actor: User = get_user_model().objects.create_user(
            username="prevencion_escala",
        )
        self.actor.groups.add(Group.objects.get(name="Prevencionista"))
        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM-ESCALA",
            nombre="Bodega de escala",
            tipo=CentroCosto.Tipo.BODEGA,
        )
        self.obligaciones = [self._obligacion(numero) for numero in range(3)]
        self.siguiente_rut = 10000000

    def _obligacion(self, numero: int) -> Obligacion:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre=f"Capacitación {numero}",
            norma_origen="Norma de prueba",
            titular=TitularObligacion.TRABAJADOR,
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.actor,
            motivo="Alta para medir la escala.",
        )
        return obligacion

    def _incorporar(self, cuantos: int) -> None:
        for _ in range(cuantos):
            cuerpo = str(self.siguiente_rut)
            self.siguiente_rut += 1
            trabajador = Trabajador.objects.create(
                rut=f"{cuerpo}-{digito_verificador(cuerpo)}",
                nombre=f"Persona {cuerpo}",
                cargo="Auxiliar de bodega",
                creado_por=self.actor,
            )
            AsignacionTrabajador.objects.create(
                trabajador=trabajador,
                centro_costo=self.centro,
                tipo=TipoAsignacion.ALTA,
                motivo="Alta de prueba.",
                autor=self.actor,
            )
            ValidacionTrabajador.objects.create(
                trabajador=trabajador,
                validado_por=self.actor,
            )
            for obligacion in self.obligaciones:
                CambioAplicabilidad.objects.create(
                    trabajador=trabajador,
                    obligacion=obligacion,
                    aplica=True,
                    motivo="Plan confirmado de prueba.",
                    autor=self.actor,
                )

    def _consultas_de_la_bandeja(self) -> int:
        with CaptureQueriesContext(connection) as consultas:
            casos_de_cumplimiento(en_fecha=EN_FECHA)
        return len(consultas)

    def _consultas_del_plan(self) -> int:
        with CaptureQueriesContext(connection) as consultas:
            for obligacion in self.obligaciones:
                caso_de_cumplimiento(
                    centro=self.centro,
                    obligacion=obligacion,
                    en_fecha=EN_FECHA,
                )
        return len(consultas)

    def test_la_bandeja_no_consulta_mas_por_tener_mas_dotacion(self) -> None:
        self._incorporar(4)
        con_pocos = self._consultas_de_la_bandeja()

        self._incorporar(20)
        con_muchos = self._consultas_de_la_bandeja()

        self.assertEqual(
            Trabajador.objects.count() * len(self.obligaciones),
            CambioAplicabilidad.objects.count(),
        )
        self.assertEqual(con_muchos, con_pocos)

    def test_el_plan_del_centro_no_consulta_mas_por_tener_mas_dotacion(self) -> None:
        self._incorporar(4)
        con_pocos = self._consultas_del_plan()

        self._incorporar(20)
        con_muchos = self._consultas_del_plan()

        self.assertEqual(con_muchos, con_pocos)

    def test_la_bandeja_enumera_un_caso_por_persona_y_obligacion(self) -> None:
        self._incorporar(6)

        casos = casos_de_cumplimiento(en_fecha=EN_FECHA)

        self.assertEqual(len(casos), 6 * len(self.obligaciones))
        self.assertTrue(all(caso.trabajador is not None for caso in casos))
