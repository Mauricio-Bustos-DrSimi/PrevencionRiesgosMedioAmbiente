"""Recorrido de aceptación del MVP, ejecutado contra PostgreSQL."""

import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import cast
from unittest import skipUnless
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from aceptacion.reloj import reloj_en
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia
from obligaciones.models import Obligacion
from trabajadores.models import Trabajador


CLAVE_PRUEBA = "clave-segura-de-prueba"
ZONA = ZoneInfo("America/Santiago")

CODIGO_CENTRO = "FAR-ACEP-001"
NOMBRE_CENTRO = "Farmacia Recorrido de Aceptación"
CODIGO_DESTINO = "FAR-ACEP-002"
NOMBRE_DESTINO = "Farmacia Recorrido de Traslado"
EXTINTORES = "Mantener extintores certificados"
RESIDUOS = "Declarar residuos peligrosos del centro"
LICENCIA = "Licencia de conducir vigente"

CARGO = "Operador de maquinaria"
RUT_TRABAJADOR = "12.345.678-5"
RUT_CANONICO = "12345678-5"
NOMBRE_TRABAJADOR = "Persona del Recorrido"
RUT_SIN_LICENCIA = "22222222-2"
NOMBRE_SIN_LICENCIA = "Persona sin Licencia"

EMISOR_INICIAL = "Certificadora inicial"
EMISOR_RENOVACION = "Certificadora de renovación"
EMISOR_ESCANEO = "Escaneo sin fecha legible"
EMISOR_LICENCIA_RENOVADA = "Municipalidad, licencia renovada"

MOTIVO_APLICA = "Aplica al centro de costo del piloto."
MOTIVO_NO_APLICA = "El centro no genera residuos peligrosos declarables."
MOTIVO_PLAN_PERSONA = "Conduce el furgón de reparto del centro."
MOTIVO_ALTA_PERSONA = "Ingresa a la dotación del centro de costo del piloto."
MOTIVO_CORRECCION = "El escaneo no traía capa de texto; Prevención leyó la fecha del papel."
MOTIVO_TRASLADO = "Se traslada al centro de costo vecino por reorganización."
MOTIVO_BAJA = "Egresa de la empresa; su historia se conserva íntegra."

MOMENTO_ALTA = datetime(2026, 9, 1, 9, tzinfo=ZONA)
MOMENTO_CARGA = datetime(2026, 9, 2, 9, tzinfo=ZONA)
MOMENTO_VALIDACION = datetime(2026, 9, 3, 9, tzinfo=ZONA)
MOMENTO_DOTACION = datetime(2026, 9, 4, 9, tzinfo=ZONA)
MOMENTO_CARGA_PERSONA = datetime(2026, 9, 5, 9, tzinfo=ZONA)
MOMENTO_CORRECCION = datetime(2026, 9, 6, 9, tzinfo=ZONA)
MOMENTO_AGREGADO = datetime(2026, 9, 7, 9, tzinfo=ZONA)
MOMENTO_VIGENTE = datetime(2026, 10, 1, 9, tzinfo=ZONA)
MOMENTO_POR_VENCER = datetime(2026, 12, 5, 9, tzinfo=ZONA)
MOMENTO_VENCIDO = datetime(2027, 1, 5, 9, tzinfo=ZONA)
MOMENTO_RENOVACION = datetime(2027, 1, 8, 9, tzinfo=ZONA)
MOMENTO_RENOVADA = datetime(2027, 1, 9, 9, tzinfo=ZONA)
MOMENTO_TRASLADO = datetime(2027, 1, 12, 9, tzinfo=ZONA)
MOMENTO_BAJA = datetime(2027, 1, 15, 9, tzinfo=ZONA)


@override_settings(DIAS_POR_VENCER=30)
@skipUnless(
    connection.vendor == "postgresql",
    "El recorrido de aceptación del MVP debe ejecutarse contra PostgreSQL; "
    "consulta docs/recorrido-aceptacion-mvp.md.",
)
class RecorridoAceptacionMvpTests(TestCase):
    """Demuestra el ciclo completo del piloto por sus interfaces públicas."""

    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        override_media.enable()
        self.addCleanup(override_media.disable)

        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_aceptacion",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_aceptacion",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista.groups.add(Group.objects.get(name="Prevencionista"))

    # Utilidades del recorrido

    def _obtener(self, nombre_url: str, *args: object, **filtros: str) -> HttpResponse:
        url = reverse(nombre_url, args=args)
        if filtros:
            url = f"{url}?" + "&".join(
                f"{clave}={valor}" for clave, valor in filtros.items()
            )
        return cast(HttpResponse, self.client.get(url))

    def _fila_del_plan(self, respuesta: HttpResponse, obligacion: str) -> str:
        """Devuelve el texto que el plan muestra para esa obligación."""
        for fragmento in re.findall(
            r"<li>(.*?)</li>",
            respuesta.content.decode(),
            re.DOTALL,
        ):
            texto = " ".join(re.sub(r"<[^>]+>", " ", fragmento).split())
            if texto.startswith(obligacion):
                return texto
        self.fail(f"El plan de aplicación no muestra la obligación {obligacion}.")

    def _crear_obligacion_en_admin(
        self,
        *,
        nombre: str,
        norma_origen: str,
        periodicidad: str,
        tipos_centro: list[str],
        titular: str = "centro_costo",
        cargos_sugeridos: str = "",
    ) -> Obligacion:
        respuesta = self.client.post(
            reverse("admin:obligaciones_obligacion_add"),
            {
                "nombre": nombre,
                "norma_origen": norma_origen,
                "titular": titular,
                "periodicidad": periodicidad,
                "tipos_centro": tipos_centro,
                "cargos_sugeridos": cargos_sugeridos,
                "motivo": f"Alta de {nombre} para el recorrido de aceptación.",
                "_save": "Guardar",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        return Obligacion.objects.get(versiones__nombre=nombre)

    def _cambiar_aplicabilidad(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        *,
        aplica: bool,
        motivo: str,
    ) -> None:
        nombre_url = (
            "planes_aplicacion:agregar" if aplica else "planes_aplicacion:no_aplica"
        )
        respuesta = self.client.post(
            reverse(nombre_url, args=[centro.pk]),
            {"obligacion": str(obligacion.pk), "motivo": motivo},
        )
        self.assertEqual(respuesta.status_code, 302)

    def _enviar_evidencia(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        *,
        emisor: str,
        fecha_emision: str,
        fecha_vencimiento: str,
        trabajador: Trabajador | None = None,
    ) -> HttpResponse:
        datos: dict[str, object] = {
            "emisor": emisor,
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "archivo": SimpleUploadedFile(
                "evidencia.pdf",
                f"Contenido firmado por {emisor}".encode(),
                content_type="application/pdf",
            ),
        }
        if trabajador is not None:
            datos["trabajador"] = str(trabajador.pk)
        return cast(
            HttpResponse,
            self.client.post(
                reverse("evidencias:cargar", args=[centro.pk, obligacion.pk]),
                datos,
            ),
        )

    def _cargar_evidencia(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        *,
        emisor: str,
        fecha_emision: str,
        fecha_vencimiento: str,
        trabajador: Trabajador | None = None,
    ) -> tuple[HttpResponse, Evidencia]:
        respuesta = self._enviar_evidencia(
            centro,
            obligacion,
            emisor=emisor,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            trabajador=trabajador,
        )
        self.assertEqual(respuesta.status_code, 200)
        evidencia = Evidencia.objects.filter(
            centro_costo=centro,
            obligacion=obligacion,
            emisor=emisor,
        ).first()
        assert evidencia is not None
        return respuesta, evidencia

    # Etapas del recorrido

    def _autenticarse(self, usuario: User) -> None:
        respuesta = self.client.post(
            reverse("iniciar_sesion"),
            {"username": usuario.username, "password": CLAVE_PRUEBA},
        )
        self.assertRedirects(respuesta, reverse("inicio"))

    def _partir_desde_la_autenticacion(self) -> None:
        anonima = self._obtener("inicio")

        self.assertRedirects(
            anonima,
            f"{reverse('iniciar_sesion')}?next={reverse('inicio')}",
        )

        self._autenticarse(self.prevencionista)
        portada = self._obtener("inicio")

        self.assertContains(portada, self.prevencionista.username)
        self.assertContains(portada, reverse("evidencias:operacion"))
        self.assertContains(portada, reverse("evidencias:vencimientos"))
        self.assertContains(portada, reverse("evidencias:pendientes"))

    def _crear_centro_en_admin(self, codigo: str, nombre: str) -> CentroCosto:
        respuesta = self.client.post(
            reverse("admin:centros_costo_centrocosto_add"),
            {
                "codigo_contable": codigo,
                "nombre": nombre,
                "tipo": CentroCosto.Tipo.FARMACIA,
                "cve_unidad": "CL-4410",
                "_save": "Guardar",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        return CentroCosto.objects.get(codigo_contable=codigo)

    def _configurar_el_piloto(
        self,
    ) -> tuple[CentroCosto, Obligacion, Obligacion, Obligacion]:
        with reloj_en(MOMENTO_ALTA):
            self._autenticarse(self.sysadmin)
            centro = self._crear_centro_en_admin(CODIGO_CENTRO, NOMBRE_CENTRO)
            self._crear_centro_en_admin(CODIGO_DESTINO, NOMBRE_DESTINO)

            extintores = self._crear_obligacion_en_admin(
                nombre=EXTINTORES,
                norma_origen="DS 594, artículo 45",
                periodicidad="anual",
                tipos_centro=[CentroCosto.Tipo.FARMACIA],
            )
            residuos = self._crear_obligacion_en_admin(
                nombre=RESIDUOS,
                norma_origen="DS 148",
                periodicidad="anual",
                tipos_centro=[],
            )
            # Una obligación que no es de la instalación sino de quien conduce.
            # Una farmacia no tiene licencia de conducir.
            licencia = self._crear_obligacion_en_admin(
                nombre=LICENCIA,
                norma_origen="Ley 18.290, ley de tránsito",
                periodicidad="anual",
                tipos_centro=[],
                titular="trabajador",
                cargos_sugeridos=CARGO,
            )

            self._autenticarse(self.prevencionista)
            self._cambiar_aplicabilidad(
                centro,
                extintores,
                aplica=True,
                motivo=MOTIVO_APLICA,
            )
            self._cambiar_aplicabilidad(
                centro,
                residuos,
                aplica=True,
                motivo=MOTIVO_APLICA,
            )

            sin_evidencia = self._obtener(
                "evidencias:operacion",
                estado="sin_evidencia",
            )
            como_vencido = self._obtener("evidencias:operacion", estado="vencido")
            como_vigente = self._obtener("evidencias:operacion", estado="vigente")
            vencimientos = self._obtener("evidencias:vencimientos")

        url_cargar_extintores = reverse(
            "evidencias:cargar",
            args=[centro.pk, extintores.pk],
        )
        self.assertContains(sin_evidencia, url_cargar_extintores)
        self.assertContains(
            sin_evidencia,
            reverse("evidencias:cargar", args=[centro.pk, residuos.pk]),
        )
        # Una obligación nunca acreditada no es una vencida ni una cumplida:
        # el filtro tiene que excluirla de ambos estados, no solo listarla en el
        # suyo.
        self.assertNotContains(como_vencido, url_cargar_extintores)
        self.assertContains(
            como_vencido,
            "No hay obligaciones configuradas en el piloto.",
        )
        self.assertNotContains(como_vigente, url_cargar_extintores)
        self.assertContains(vencimientos, "No hay obligaciones vencidas ni por vencer.")
        return centro, extintores, residuos, licencia

    def _cargar_sin_producir_cumplimiento(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
    ) -> Evidencia:
        with reloj_en(MOMENTO_CARGA):
            self.client.force_login(self.prevencionista)
            confirmacion, evidencia = self._cargar_evidencia(
                centro,
                obligacion,
                emisor=EMISOR_INICIAL,
                fecha_emision="2026-09-01",
                fecha_vencimiento="2026-12-31",
            )
            bandeja = self._obtener("evidencias:pendientes")
            detalle = self._obtener("evidencias:validar", evidencia.pk)
            vigentes = self._obtener("evidencias:operacion", estado="vigente")
            pendientes = self._obtener(
                "evidencias:operacion",
                estado="pendiente_validacion",
            )

        url_evidencia = reverse("evidencias:validar", args=[evidencia.pk])
        self.assertContains(confirmacion, "Pendiente de validación")
        self.assertContains(confirmacion, evidencia.hash_sha256)
        self.assertContains(bandeja, url_evidencia)
        self.assertContains(detalle, "Pendiente de validación — No cumplida")
        self.assertNotContains(vigentes, url_evidencia)
        self.assertContains(pendientes, url_evidencia)
        return evidencia

    def _validar_y_derivar_vigencia(
        self,
        centro: CentroCosto,
        evidencia: Evidencia,
        residuos: Obligacion,
    ) -> None:
        with reloj_en(MOMENTO_VALIDACION):
            self.client.force_login(self.prevencionista)
            validacion = self.client.post(
                reverse("evidencias:validar", args=[evidencia.pk]),
            )
            self.assertEqual(validacion.status_code, 302)
            self._cambiar_aplicabilidad(
                centro,
                residuos,
                aplica=False,
                motivo=MOTIVO_NO_APLICA,
            )
            detalle = self._obtener("evidencias:validar", evidencia.pk)
            vigentes = self._obtener("evidencias:operacion", estado="vigente")
            bandeja = self._obtener("evidencias:pendientes")
            plan = self._obtener("planes_aplicacion:plan", centro.pk)

        self.assertContains(detalle, "Vigente")
        self.assertNotContains(detalle, "No cumplida")
        self.assertContains(detalle, f"Validada por {self.prevencionista.username}")
        self.assertContains(
            vigentes,
            reverse("evidencias:validar", args=[evidencia.pk]),
        )
        self.assertContains(bandeja, "No hay evidencias pendientes de validación.")
        self.assertIn("Vigente", self._fila_del_plan(plan, EXTINTORES))
        self.assertIn("No aplica", self._fila_del_plan(plan, RESIDUOS))
        self.assertNotContains(
            plan,
            reverse("evidencias:cargar", args=[centro.pk, residuos.pk]),
        )
        self.assertContains(plan, MOTIVO_NO_APLICA)
        self.assertContains(plan, self.prevencionista.username)

    def _rechazar_la_carga_sobre_lo_que_no_aplica(
        self,
        centro: CentroCosto,
        residuos: Obligacion,
    ) -> None:
        """La exclusión del plan se hace valer en el servidor.

        Ocultar el enlace de carga solo prueba la pantalla; lo que debe quedar
        demostrado es que la obligación excluida tampoco admite evidencia
        cuando se envía el formulario directamente.
        """
        evidencias_antes = Evidencia.objects.count()

        with reloj_en(MOMENTO_VALIDACION):
            self.client.force_login(self.prevencionista)
            rechazo = cast(
                HttpResponse,
                self.client.post(
                    reverse("evidencias:cargar", args=[centro.pk, residuos.pk]),
                    {
                        "emisor": "Certificadora improcedente",
                        "fecha_emision": "2026-09-02",
                        "fecha_vencimiento": "2027-09-02",
                        "archivo": SimpleUploadedFile(
                            "improcedente.pdf",
                            b"Evidencia de una obligacion que no aplica",
                            content_type="application/pdf",
                        ),
                    },
                ),
            )

        self.assertContains(
            rechazo,
            "No aplica: no se puede cargar esta evidencia.",
            status_code=403,
        )
        self.assertEqual(Evidencia.objects.count(), evidencias_antes)

    # Etapa del trabajador: el otro titular de obligación
    #
    # Se intercala entre la validación y el paso del tiempo, porque el ciclo
    # temporal tiene que demostrarse también en el grano de la persona: es la
    # condición para abrir el piloto, y el 100 % de su material probatorio es
    # por persona.

    def _dar_de_alta(self, centro: CentroCosto, rut: str, nombre: str) -> Trabajador:
        respuesta = self.client.post(
            reverse("trabajadores:crear"),
            {
                "rut": rut,
                "nombre": nombre,
                "cargo": CARGO,
                "centro_costo": str(centro.pk),
                "motivo": MOTIVO_ALTA_PERSONA,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        return Trabajador.objects.get(nombre=nombre)

    def _incorporar_la_dotacion(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
    ) -> tuple[Trabajador, Trabajador]:
        with reloj_en(MOMENTO_DOTACION):
            self.client.force_login(self.prevencionista)
            conductora = self._dar_de_alta(
                centro,
                RUT_TRABAJADOR,
                NOMBRE_TRABAJADOR,
            )
            sin_licencia = self._dar_de_alta(
                centro,
                RUT_SIN_LICENCIA,
                NOMBRE_SIN_LICENCIA,
            )
            recien_creada = self._obtener("trabajadores:detalle", conductora.pk)

            for trabajador in (conductora, sin_licencia):
                validacion = self.client.post(
                    reverse("trabajadores:validar", args=[trabajador.pk]),
                )
                self.assertEqual(validacion.status_code, 302)
                plan = self.client.post(
                    reverse(
                        "trabajadores:confirmar_sugerencia",
                        args=[trabajador.pk],
                    ),
                    {"motivo": MOTIVO_PLAN_PERSONA},
                )
                self.assertEqual(plan.status_code, 302)

            confirmada = self._obtener("trabajadores:detalle", conductora.pk)

        # El RUT es la identidad y se guarda en una sola forma, aunque se haya
        # escrito con puntos.
        self.assertEqual(conductora.rut, RUT_CANONICO)
        self.assertContains(recien_creada, "No validado")
        self.assertContains(confirmada, LICENCIA)
        self.assertContains(confirmada, "Sin evidencia")
        self.assertNotContains(confirmada, "No validado")
        # La obligación de la persona no la exige el centro por su tipo: la
        # sugiere su cargo y la confirma Prevención, una por una.
        self.assertContains(confirmada, CARGO)
        return conductora, sin_licencia

    def _cargar_a_nombre_de_la_persona(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
        conductora: Trabajador,
    ) -> Evidencia:
        evidencias_antes = Evidencia.objects.count()

        with reloj_en(MOMENTO_CARGA_PERSONA):
            self.client.force_login(self.prevencionista)
            sin_persona = self._enviar_evidencia(
                centro,
                licencia,
                emisor=EMISOR_ESCANEO,
                fecha_emision="2026-09-05",
                fecha_vencimiento="2026-09-06",
            )
            _, escaneo = self._cargar_evidencia(
                centro,
                licencia,
                emisor=EMISOR_ESCANEO,
                fecha_emision="2026-09-05",
                fecha_vencimiento="2026-09-06",
                trabajador=conductora,
            )
            bandeja = self._obtener("evidencias:pendientes")

        self.assertContains(
            sin_persona,
            "tiene que indicar a qué persona acredita",
            status_code=403,
        )
        self.assertEqual(Evidencia.objects.count(), evidencias_antes + 1)
        self.assertEqual(escaneo.trabajador, conductora)
        # La bandeja tiene que decir a quién citar, no cuántos faltan.
        self.assertContains(bandeja, NOMBRE_TRABAJADOR)
        self.assertContains(bandeja, RUT_CANONICO)
        return escaneo

    def _validar_corrigiendo_la_fecha(self, escaneo: Evidencia) -> None:
        """El escaneo no declaraba su fecha; Prevención la lee y la confirma.

        Corregir no es renovar: no llegó otro documento. El archivo y su hash
        siguen siendo los de la carga, y la vigencia pasa a derivarse del dato
        confirmado.
        """
        hash_original = escaneo.hash_sha256
        emision_cargada = escaneo.fecha_emision

        with reloj_en(MOMENTO_CORRECCION):
            self.client.force_login(self.prevencionista)
            correccion = self.client.post(
                reverse("evidencias:validar", args=[escaneo.pk]),
                {
                    "corregir_fechas": "on",
                    "fecha_emision": "2026-06-20",
                    "fecha_vencimiento": "2026-12-20",
                    "motivo": MOTIVO_CORRECCION,
                },
            )
            self.assertEqual(correccion.status_code, 302)
            detalle = self._obtener("evidencias:validar", escaneo.pk)
            integridad = self._obtener(
                "evidencias:verificar_integridad",
                escaneo.pk,
            )

        guardada = Evidencia.objects.get(pk=escaneo.pk)
        self.assertEqual(guardada.hash_sha256, hash_original)
        self.assertEqual(guardada.fecha_emision, emision_cargada)
        self.assertContains(integridad, "Coincide")
        # Lo que se sabía al cargar y lo que se confirmó después conviven en la
        # pantalla: el fiscalizador tiene que poder comparar los dos.
        self.assertContains(detalle, "Fecha de emisión con que se cargó")
        self.assertContains(detalle, "Fecha de emisión corregida")
        self.assertContains(detalle, MOTIVO_CORRECCION)
        self.assertContains(detalle, "Vigente")
        self.assertNotContains(detalle, "No cumplida")

    def _ver_el_agregado_y_su_desglose(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
        conductora: Trabajador,
        sin_licencia: Trabajador,
    ) -> None:
        with reloj_en(MOMENTO_AGREGADO):
            self.client.force_login(self.prevencionista)
            plan = self._obtener("planes_aplicacion:plan", centro.pk)
            desglose = self._obtener(
                "planes_aplicacion:desglose",
                centro.pk,
                licencia.pk,
            )

        fila = self._fila_del_plan(plan, LICENCIA)
        # El peor estado presente manda: una sola persona sin cobertura no
        # puede quedar escondida detrás de la que sí la tiene.
        self.assertIn("Sin evidencia", fila)
        self.assertIn("1 de 2 trabajadores", fila)
        self.assertIn("Vigente: 1", fila)
        self.assertContains(
            plan,
            reverse("planes_aplicacion:desglose", args=[centro.pk, licencia.pk]),
        )
        self.assertContains(desglose, NOMBRE_TRABAJADOR)
        self.assertContains(desglose, NOMBRE_SIN_LICENCIA)
        self.assertContains(desglose, "Sin evidencia")
        self.assertContains(desglose, "Vigente")
        self.assertContains(
            desglose,
            reverse("trabajadores:detalle", args=[conductora.pk]),
        )
        self.assertContains(
            desglose,
            reverse("trabajadores:detalle", args=[sin_licencia.pk]),
        )

    def _observar_el_paso_del_tiempo_de_la_persona(
        self,
        conductora: Trabajador,
        escaneo: Evidencia,
    ) -> None:
        url_escaneo = reverse("evidencias:validar", args=[escaneo.pk])

        with reloj_en(MOMENTO_POR_VENCER):
            self.client.force_login(self.prevencionista)
            por_vencer = self._obtener("evidencias:vencimientos", estado="por_vencer")
            filtrada = self._obtener(
                "evidencias:vencimientos",
                estado="por_vencer",
                trabajador=str(conductora.pk),
            )

        self.assertContains(por_vencer, url_escaneo)
        self.assertContains(por_vencer, NOMBRE_TRABAJADOR)
        self.assertContains(filtrada, url_escaneo)

        with reloj_en(MOMENTO_VENCIDO):
            self.client.force_login(self.prevencionista)
            vencido = self._obtener("evidencias:vencimientos", estado="vencido")
            detalle = self._obtener("trabajadores:detalle", conductora.pk)

        self.assertContains(vencido, url_escaneo)
        self.assertContains(vencido, NOMBRE_TRABAJADOR)
        self.assertContains(detalle, "Vencido")

    def _renovar_la_licencia_de_la_persona(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
        conductora: Trabajador,
        escaneo: Evidencia,
    ) -> Evidencia:
        with reloj_en(MOMENTO_RENOVACION):
            self.client.force_login(self.prevencionista)
            _, renovada = self._cargar_evidencia(
                centro,
                licencia,
                emisor=EMISOR_LICENCIA_RENOVADA,
                fecha_emision="2027-01-06",
                fecha_vencimiento="2027-12-31",
                trabajador=conductora,
            )

        with reloj_en(MOMENTO_RENOVADA):
            self.client.force_login(self.prevencionista)
            validacion = self.client.post(
                reverse("evidencias:validar", args=[renovada.pk]),
            )
            self.assertEqual(validacion.status_code, 302)
            detalle = self._obtener("trabajadores:detalle", conductora.pk)

        self.assertContains(detalle, "Vigente")
        # La anterior no desaparece: sigue consultable y su archivo sigue ahí.
        self.assertTrue(Path(escaneo.archivo.path).exists())
        return renovada

    def _trasladar_sin_perder_lo_acreditado(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
        conductora: Trabajador,
        escaneo: Evidencia,
    ) -> None:
        destino = CentroCosto.objects.get(codigo_contable=CODIGO_DESTINO)

        with reloj_en(MOMENTO_TRASLADO):
            self.client.force_login(self.prevencionista)
            traslado = self.client.post(
                reverse("trabajadores:trasladar", args=[conductora.pk]),
                {"centro_costo": str(destino.pk), "motivo": MOTIVO_TRASLADO},
            )
            self.assertEqual(traslado.status_code, 302)
            origen_hoy = self._obtener(
                "planes_aplicacion:desglose",
                centro.pk,
                licencia.pk,
            )
            destino_hoy = self._obtener(
                "planes_aplicacion:desglose",
                destino.pk,
                licencia.pk,
            )
            url_origen = reverse(
                "planes_aplicacion:desglose",
                args=[centro.pk, licencia.pk],
            )
            origen_antes = cast(
                HttpResponse,
                self.client.get(f"{url_origen}?fecha=2026-12-05"),
            )

        self.assertNotContains(origen_hoy, NOMBRE_TRABAJADOR)
        self.assertContains(origen_hoy, NOMBRE_SIN_LICENCIA)
        self.assertContains(destino_hoy, NOMBRE_TRABAJADOR)
        # La reconstrucción histórica usa la dotación de esa fecha, no la de
        # hoy: en diciembre la persona todavía respondía por el centro origen.
        self.assertContains(origen_antes, NOMBRE_TRABAJADOR)
        self.assertContains(origen_antes, "Por vencer")
        # Lo que acreditó donde estaba sigue asociado a ese centro de costo.
        self.assertEqual(
            Evidencia.objects.get(pk=escaneo.pk).centro_costo,
            centro,
        )

    def _dar_de_baja_sin_borrar_la_historia(
        self,
        licencia: Obligacion,
        conductora: Trabajador,
    ) -> None:
        destino = CentroCosto.objects.get(codigo_contable=CODIGO_DESTINO)

        with reloj_en(MOMENTO_BAJA):
            self.client.force_login(self.prevencionista)
            baja = self.client.post(
                reverse("trabajadores:dar_de_baja", args=[conductora.pk]),
                {"motivo": MOTIVO_BAJA},
            )
            self.assertEqual(baja.status_code, 302)
            desglose = self._obtener(
                "planes_aplicacion:desglose",
                destino.pk,
                licencia.pk,
            )
            detalle = self._obtener("trabajadores:detalle", conductora.pk)
            operacion = self._obtener(
                "evidencias:operacion",
                trabajador=str(conductora.pk),
            )

        # Deja de exigirse, pero nada se borró: la baja es un cierre con
        # motivo y la historia sigue en pantalla.
        self.assertNotContains(desglose, NOMBRE_TRABAJADOR)
        self.assertContains(
            operacion,
            "No hay obligaciones configuradas en el piloto.",
        )
        self.assertContains(detalle, "Dado de baja")
        self.assertContains(detalle, MOTIVO_BAJA)
        self.assertContains(detalle, MOTIVO_TRASLADO)
        self.assertContains(detalle, MOTIVO_ALTA_PERSONA)

    def _observar_el_paso_del_tiempo(
        self,
        centro: CentroCosto,
        evidencia: Evidencia,
    ) -> None:
        url_evidencia = reverse("evidencias:validar", args=[evidencia.pk])

        with reloj_en(MOMENTO_VIGENTE):
            self.client.force_login(self.prevencionista)
            vigentes = self._obtener("evidencias:operacion", estado="vigente")
            tranquilo = self._obtener("evidencias:vencimientos")

        self.assertContains(vigentes, url_evidencia)
        self.assertContains(tranquilo, "No hay obligaciones vencidas ni por vencer.")

        with reloj_en(MOMENTO_POR_VENCER):
            self.client.force_login(self.prevencionista)
            por_vencer = self._obtener("evidencias:vencimientos", estado="por_vencer")
            aun_no_vencido = self._obtener("evidencias:vencimientos", estado="vencido")

        self.assertContains(por_vencer, url_evidencia)
        self.assertContains(por_vencer, "Umbral de Por vencer: 30 días")
        self.assertNotContains(aun_no_vencido, url_evidencia)

        with reloj_en(MOMENTO_VENCIDO):
            self.client.force_login(self.prevencionista)
            vencido = self._obtener("evidencias:vencimientos", estado="vencido")
            ya_no_por_vencer = self._obtener(
                "evidencias:vencimientos",
                estado="por_vencer",
            )
            plan = self._obtener("planes_aplicacion:plan", centro.pk)

        self.assertContains(vencido, url_evidencia)
        self.assertNotContains(ya_no_por_vencer, url_evidencia)
        self.assertIn("Vencido", self._fila_del_plan(plan, EXTINTORES))

    def _renovar_conservando_la_evidencia_anterior(
        self,
        centro: CentroCosto,
        obligacion: Obligacion,
        anterior: Evidencia,
    ) -> Evidencia:
        with reloj_en(MOMENTO_RENOVACION):
            self.client.force_login(self.prevencionista)
            _, renovada = self._cargar_evidencia(
                centro,
                obligacion,
                emisor=EMISOR_RENOVACION,
                fecha_emision="2027-01-06",
                fecha_vencimiento="2027-12-31",
            )

        with reloj_en(MOMENTO_RENOVADA):
            self.client.force_login(self.prevencionista)
            validacion = self.client.post(
                reverse("evidencias:validar", args=[renovada.pk]),
            )
            self.assertEqual(validacion.status_code, 302)
            detalle_renovada = self._obtener("evidencias:validar", renovada.pk)
            detalle_anterior = self._obtener("evidencias:validar", anterior.pk)
            vigentes = self._obtener("evidencias:operacion", estado="vigente")
            plan = self._obtener("planes_aplicacion:plan", centro.pk)

        self.assertContains(detalle_renovada, "Vigente")
        self.assertContains(detalle_renovada, EMISOR_INICIAL)
        self.assertContains(detalle_renovada, EMISOR_RENOVACION)
        self.assertContains(
            detalle_renovada,
            reverse("evidencias:validar", args=[anterior.pk]),
        )
        self.assertContains(detalle_anterior, EMISOR_INICIAL)
        self.assertContains(
            vigentes,
            reverse("evidencias:validar", args=[renovada.pk]),
        )
        self.assertIn("Vigente", self._fila_del_plan(plan, EXTINTORES))
        self.assertTrue(Path(anterior.archivo.path).exists())
        return renovada

    def _reconstruir_fechas_pasadas(
        self,
        centro: CentroCosto,
        anterior: Evidencia,
        renovada: Evidencia,
    ) -> None:
        self.client.force_login(self.prevencionista)
        url_plan = reverse("planes_aplicacion:plan", args=[centro.pk])

        def en(fecha: str) -> HttpResponse:
            return cast(HttpResponse, self.client.get(f"{url_plan}?fecha={fecha}"))

        alta = en("2026-09-01")
        carga = en("2026-09-02")
        vigente = en("2026-10-01")
        por_vencer = en("2026-12-05")
        vencido = en("2027-01-05")
        renovado = en("2027-01-09")

        self.assertIn("Sin evidencia", self._fila_del_plan(alta, EXTINTORES))
        self.assertIn("Sin evidencia", self._fila_del_plan(alta, RESIDUOS))
        self.assertIn(
            "Pendiente de validación",
            self._fila_del_plan(carga, EXTINTORES),
        )
        self.assertIn("Vigente", self._fila_del_plan(vigente, EXTINTORES))
        self.assertIn("Por vencer", self._fila_del_plan(por_vencer, EXTINTORES))
        self.assertIn("No aplica", self._fila_del_plan(por_vencer, RESIDUOS))
        self.assertIn("Vencido", self._fila_del_plan(vencido, EXTINTORES))
        self.assertContains(
            vencido,
            reverse("evidencias:validar", args=[anterior.pk]),
        )
        self.assertNotContains(
            vencido,
            reverse("evidencias:validar", args=[renovada.pk]),
        )
        self.assertIn("Vigente", self._fila_del_plan(renovado, EXTINTORES))
        self.assertContains(
            renovado,
            reverse("evidencias:validar", args=[renovada.pk]),
        )

    def _exhibir_bitacora_e_integridad(
        self,
        centro: CentroCosto,
        extintores: Obligacion,
        residuos: Obligacion,
        anterior: Evidencia,
        renovada: Evidencia,
    ) -> None:
        self.client.force_login(self.prevencionista)
        url_recorrido = reverse(
            "bitacora:recorrido",
            args=[centro.pk, extintores.pk],
        )

        recorrido = cast(HttpResponse, self.client.get(url_recorrido))

        self.assertContains(recorrido, "Recorrido de trazabilidad")
        for encabezado in ("Qué ocurrió", "Quién actuó", "Cómo", "Cuándo"):
            self.assertContains(recorrido, encabezado)
        # Cada acto se reconoce por lo que la bitácora dice que ocurrió, y no
        # por una palabra suelta que podría aparecer en cualquier otra parte de
        # la página.
        for descripcion in (
            f"Creó el centro de costo {NOMBRE_CENTRO}.",
            f"Se registró {EXTINTORES}.",
            f"Actualizó la aplicabilidad de {EXTINTORES}.",
            f"Cargó evidencia para {EXTINTORES}.",
            f"Validó evidencia para {EXTINTORES}",
        ):
            self.assertContains(recorrido, descripcion)
        self.assertContains(recorrido, self.sysadmin.username)
        self.assertContains(recorrido, self.prevencionista.username)
        self.assertContains(recorrido, "Panel administrativo")
        self.assertContains(recorrido, MOTIVO_APLICA)
        self.assertContains(recorrido, EMISOR_INICIAL)
        self.assertContains(recorrido, EMISOR_RENOVACION)

        integridad_anterior = self._obtener(
            "evidencias:verificar_integridad",
            anterior.pk,
        )
        integridad_renovada = self._obtener(
            "evidencias:verificar_integridad",
            renovada.pk,
        )

        self.assertContains(integridad_anterior, "Coincide")
        self.assertContains(integridad_anterior, anterior.hash_sha256, count=2)
        self.assertContains(integridad_renovada, "Coincide")
        self.assertContains(integridad_renovada, renovada.hash_sha256, count=2)

        Path(anterior.archivo.path).write_bytes(b"contenido sustituido")
        alterada = self._obtener("evidencias:verificar_integridad", anterior.pk)
        recorrido_final = cast(HttpResponse, self.client.get(url_recorrido))

        self.assertContains(alterada, "No coincide — Alteración detectada")
        self.assertContains(alterada, anterior.hash_sha256)
        self.assertContains(recorrido_final, "Coincidió")
        self.assertContains(recorrido_final, "No coincidió")

        recorrido_residuos = cast(
            HttpResponse,
            self.client.get(
                reverse("bitacora:recorrido", args=[centro.pk, residuos.pk]),
            ),
        )

        self.assertContains(recorrido_residuos, "declarar_no_aplica")
        self.assertContains(recorrido_residuos, MOTIVO_NO_APLICA)

    def _exhibir_la_bitacora_de_la_persona(
        self,
        centro: CentroCosto,
        licencia: Obligacion,
    ) -> None:
        """Alta, corrección y validación son actos distintos y se leen así."""
        self.client.force_login(self.prevencionista)

        recorrido = self._obtener("bitacora:recorrido", centro.pk, licencia.pk)

        for descripcion in (
            f"Dio de alta a {NOMBRE_TRABAJADOR} ({RUT_CANONICO})",
            f"Incorporó a {NOMBRE_TRABAJADOR} ({RUT_CANONICO}) a la dotación",
            f"Cargó evidencia para {LICENCIA} a nombre de {NOMBRE_TRABAJADOR}",
            "Corrigió las fechas leídas del documento",
            f"Validó evidencia para {LICENCIA}",
        ):
            self.assertContains(recorrido, descripcion)
        # Los dos canales: el catálogo entró por el panel administrativo y la
        # operación de la persona por las pantallas propias.
        self.assertContains(recorrido, "Panel administrativo")
        self.assertContains(recorrido, "web")
        self.assertContains(recorrido, "corregir_fechas_evidencia")
        self.assertContains(recorrido, "validar_evidencia")
        self.assertContains(recorrido, MOTIVO_CORRECCION)
        self.assertContains(recorrido, MOTIVO_PLAN_PERSONA)

        # El traslado es un acto sobre la dotación del centro de destino: ahí
        # queda, con su autor y su motivo.
        destino = CentroCosto.objects.get(codigo_contable=CODIGO_DESTINO)
        recorrido_destino = self._obtener(
            "bitacora:recorrido",
            destino.pk,
            licencia.pk,
        )

        self.assertContains(recorrido_destino, f"Trasladó a {NOMBRE_TRABAJADOR}")
        self.assertContains(recorrido_destino, MOTIVO_TRASLADO)

    def test_el_piloto_recorre_el_ciclo_completo_de_aceptacion(self) -> None:
        self._partir_desde_la_autenticacion()
        centro, extintores, residuos, licencia = self._configurar_el_piloto()
        anterior = self._cargar_sin_producir_cumplimiento(centro, extintores)
        self._validar_y_derivar_vigencia(centro, anterior, residuos)
        self._rechazar_la_carga_sobre_lo_que_no_aplica(centro, residuos)

        conductora, sin_licencia = self._incorporar_la_dotacion(centro, licencia)
        escaneo = self._cargar_a_nombre_de_la_persona(centro, licencia, conductora)
        self._validar_corrigiendo_la_fecha(escaneo)
        self._ver_el_agregado_y_su_desglose(
            centro,
            licencia,
            conductora,
            sin_licencia,
        )

        self._observar_el_paso_del_tiempo(centro, anterior)
        self._observar_el_paso_del_tiempo_de_la_persona(conductora, escaneo)
        renovada = self._renovar_conservando_la_evidencia_anterior(
            centro,
            extintores,
            anterior,
        )
        self._renovar_la_licencia_de_la_persona(
            centro,
            licencia,
            conductora,
            escaneo,
        )
        self._reconstruir_fechas_pasadas(centro, anterior, renovada)
        self._trasladar_sin_perder_lo_acreditado(
            centro,
            licencia,
            conductora,
            escaneo,
        )
        self._dar_de_baja_sin_borrar_la_historia(licencia, conductora)
        self._exhibir_bitacora_e_integridad(
            centro,
            extintores,
            residuos,
            anterior,
            renovada,
        )
        self._exhibir_la_bitacora_de_la_persona(centro, licencia)
