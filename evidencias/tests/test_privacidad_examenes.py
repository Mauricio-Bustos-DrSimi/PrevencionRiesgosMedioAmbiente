import hashlib
import importlib
import tempfile
from collections.abc import Iterable
from datetime import date
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.http import FileResponse
from django.test import TestCase
from django.urls import reverse

from bitacora.models import EventoBitacora
from bitacora.registro import ContextoBitacora, registrar_evento
from acceso.permisos import exigir_acceso_evidencia, puede_acceder_version_evidencia
from acceso.models import AsignacionEncargadoCentro, TipoAsignacionEncargado
from centros_costo.models import CentroCosto
from evidencias.models import Evidencia, exigir_titular_coherente
from evidencias.services import cargar_evidencia, corregir_evidencia, validar_evidencia
from importaciones.catalogo_demo import CATALOGO
from obligaciones.models import (
    ClasificacionEvidencia,
    Obligacion,
    TipoVersion,
    VersionObligacion,
)
from trabajadores.models import AsignacionTrabajador, TipoAsignacion, Trabajador
from planes_aplicacion.models import CambioAplicabilidad


CLAVE_PRUEBA = "clave-segura-de-prueba"
CONTENIDO = b"contenido medico estrictamente ficticio"


class PrivacidadExamenesOcupacionalesTests(TestCase):
    def setUp(self) -> None:
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self._override_media = self.settings(MEDIA_ROOT=self.directorio_temporal.name)
        self._override_media.enable()
        self.addCleanup(self._override_media.disable)

        grupo_prevencion = Group.objects.get(name="Prevencionista")
        self.prevencionista = get_user_model().objects.create_user(
            username="prevencionista_salud",
            password=CLAVE_PRUEBA,
        )
        self.prevencionista.groups.add(grupo_prevencion)
        self.sysadmin = get_user_model().objects.create_superuser(
            username="sysadmin_salud",
            password=CLAVE_PRUEBA,
        )
        self.usuarios_denegados = []
        for nombre_grupo in ("Encargado", "Lector"):
            usuario = get_user_model().objects.create_user(
                username=nombre_grupo.lower(),
                password=CLAVE_PRUEBA,
            )
            grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
            usuario.groups.add(grupo)
            self.usuarios_denegados.append(usuario)
        self.usuarios_denegados.append(
            get_user_model().objects.create_user(
                username="sin_rol_salud",
                password=CLAVE_PRUEBA,
            )
        )

        self.centro = CentroCosto.objects.create(
            codigo_contable="ADM-SALUD",
            nombre="Centro ficticio de salud",
            tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
        )
        AsignacionEncargadoCentro.objects.create(
            usuario=self.usuarios_denegados[0],
            centro_costo=self.centro,
            tipo=TipoAsignacionEncargado.ASIGNACION,
            motivo="Asignación ficticia para comprobar la exclusión de salud",
            autor=self.sysadmin,
        )
        self.trabajador = Trabajador.objects.create(
            rut="12345678-5",
            nombre="Persona Reservada",
            cargo="Función ficticia",
            creado_por=self.prevencionista,
        )
        AsignacionTrabajador.objects.create(
            trabajador=self.trabajador,
            centro_costo=self.centro,
            tipo=TipoAsignacion.ALTA,
            motivo="Asignación ficticia",
            autor=self.prevencionista,
        )
        self.obligacion = Obligacion.objects.create()
        self.version = VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=1,
            nombre="Examen ocupacional ficticio",
            norma_origen="Fuente ficticia",
            titular="trabajador",
            periodicidad="por_evento",
            clasificacion_evidencia=ClasificacionEvidencia.SALUD_OCUPACIONAL,
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta para prueba de privacidad",
        )
        self.evidencia = Evidencia.objects.create(
            centro_costo=self.centro,
            obligacion=self.obligacion,
            version_obligacion=self.version,
            trabajador=self.trabajador,
            archivo=SimpleUploadedFile(
                "Persona Reservada 12345678-5 examen.pdf",
                CONTENIDO,
                content_type="application/pdf",
            ),
            hash_sha256=hashlib.sha256(CONTENIDO).hexdigest(),
            emisor="Prestador ficticio",
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2027, 1, 1),
            cargada_por=self.prevencionista,
        )

    def _urls_sensibles(self) -> tuple[str, ...]:
        return (
            reverse("obligaciones:detalle", args=[self.obligacion.pk]),
            reverse("obligaciones:corregir", args=[self.obligacion.pk]),
            reverse("obligaciones:cerrar", args=[self.obligacion.pk]),
            reverse(
                "evidencias:cargar",
                args=[self.centro.pk, self.obligacion.pk],
            ),
            reverse("evidencias:validar", args=[self.evidencia.pk]),
            reverse("evidencias:corregir", args=[self.evidencia.pk]),
            reverse("evidencias:descargar", args=[self.evidencia.pk]),
            reverse("evidencias:verificar_integridad", args=[self.evidencia.pk]),
            reverse(
                "bitacora:recorrido",
                args=[self.centro.pk, self.obligacion.pk],
            ),
        )

    def test_encargado_lector_y_usuario_sin_rol_no_acceden_directamente(self) -> None:
        datos_sensibles = (
            self.trabajador.nombre,
            self.trabajador.rut,
            self.evidencia.archivo.name,
        )
        for usuario in self.usuarios_denegados:
            self.client.force_login(usuario)
            for url in self._urls_sensibles():
                with self.subTest(usuario=usuario.username, url=url):
                    respuesta = self.client.get(url)
                    self.assertEqual(respuesta.status_code, 403)
                    contenido = respuesta.content.decode(errors="replace")
                    for dato in datos_sensibles:
                        self.assertNotIn(dato, contenido)

    def test_roles_autorizados_conservan_acceso_a_la_descarga(self) -> None:
        for usuario in (self.prevencionista, self.sysadmin):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = cast(
                    FileResponse,
                    self.client.get(
                        reverse("evidencias:descargar", args=[self.evidencia.pk])
                    ),
                )
                contenido = b"".join(
                    cast(Iterable[bytes], respuesta.streaming_content)
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(contenido, CONTENIDO)

    def test_roles_autorizados_consultan_detalle_integridad_y_bitacora(self) -> None:
        urls = (
            reverse("obligaciones:detalle", args=[self.obligacion.pk]),
            reverse("evidencias:validar", args=[self.evidencia.pk]),
            reverse("evidencias:verificar_integridad", args=[self.evidencia.pk]),
            reverse(
                "bitacora:recorrido",
                args=[self.centro.pk, self.obligacion.pk],
            ),
        )
        for usuario in (self.prevencionista, self.sysadmin):
            self.client.force_login(usuario)
            for url in urls:
                with self.subTest(usuario=usuario.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_politica_sensible_rechaza_roles_denegados_por_objeto(self) -> None:
        for usuario in self.usuarios_denegados:
            with self.subTest(usuario=usuario.username):
                self.assertFalse(
                    puede_acceder_version_evidencia(usuario, self.version)
                )
                with self.assertRaises(PermissionDenied):
                    exigir_acceso_evidencia(usuario, self.evidencia)

    def test_recorrido_sin_evidencias_tambien_rechaza_roles_denegados(self) -> None:
        obligacion_sin_evidencia = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion_sin_evidencia,
            numero=1,
            nombre="Examen futuro ficticio",
            norma_origen="Fuente ficticia",
            titular="trabajador",
            periodicidad="por_evento",
            clasificacion_evidencia=ClasificacionEvidencia.SALUD_OCUPACIONAL,
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta ficticia sin archivos",
        )
        usuario = self.usuarios_denegados[0]
        self.client.force_login(usuario)

        respuesta = self.client.get(
            reverse(
                "bitacora:recorrido",
                args=[self.centro.pk, obligacion_sin_evidencia.pk],
            )
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_clasificacion_no_depende_del_nombre_de_la_obligacion(self) -> None:
        version_renombrada = VersionObligacion.objects.create(
            obligacion=self.obligacion,
            numero=2,
            nombre="Aptitud vigente",
            norma_origen="Fuente ficticia corregida",
            titular="trabajador",
            periodicidad="por_evento",
            clasificacion_evidencia=self.version.clasificacion_evidencia,
            tipo_version=TipoVersion.CORRECCION,
            autor=self.prevencionista,
            motivo="Renombre para demostrar clasificación estable",
        )
        obligacion_general = Obligacion.objects.create()
        version_general = VersionObligacion.objects.create(
            obligacion=obligacion_general,
            numero=1,
            nombre="Texto que dice examen ocupacional",
            norma_origen="Fuente ficticia",
            titular="centro_costo",
            periodicidad="anual",
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="El nombre no clasifica la evidencia",
        )

        self.assertEqual(
            version_renombrada.clasificacion_evidencia,
            ClasificacionEvidencia.SALUD_OCUPACIONAL,
        )
        self.assertEqual(
            version_general.clasificacion_evidencia,
            ClasificacionEvidencia.GENERAL,
        )

    def test_correccion_http_antigua_no_desclasifica_al_renombrar(self) -> None:
        self.client.force_login(self.prevencionista)

        respuesta = self.client.post(
            reverse("obligaciones:corregir", args=[self.obligacion.pk]),
            {
                "nombre": "Aptitud vigente",
                "norma_origen": "Fuente ficticia corregida",
                "titular": "trabajador",
                "periodicidad": "por_evento",
                "motivo": "Renombre mediante cliente sin el campo nuevo",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            self.obligacion.version_actual.clasificacion_evidencia,
            ClasificacionEvidencia.SALUD_OCUPACIONAL,
        )

    def test_catalogo_demo_clasifica_solamente_los_cuatro_examenes(self) -> None:
        clasificados = {
            nombre
            for nombre, obligacion in CATALOGO.items()
            if obligacion.clasificacion_evidencia
            == ClasificacionEvidencia.SALUD_OCUPACIONAL
        }

        self.assertEqual(
            clasificados,
            {
                "Examen ocupacional de altura física",
                "Examen ocupacional de conductor clase D",
                "Examen ocupacional de operadores de maquinaria",
                "Examen ocupacional de conductor de vehículo liviano",
            },
        )

    def test_migracion_clasifica_todas_las_versiones_de_una_obligacion(self) -> None:
        obligacion = Obligacion.objects.create()
        primera = VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=1,
            nombre="Examen ocupacional de altura física",
            norma_origen="Fuente ficticia",
            titular="trabajador",
            periodicidad="por_evento",
            tipo_version=TipoVersion.ALTA,
            autor=self.prevencionista,
            motivo="Alta ficticia",
        )
        renombrada = VersionObligacion.objects.create(
            obligacion=obligacion,
            numero=2,
            nombre="Aptitud para tarea crítica",
            norma_origen="Fuente ficticia",
            titular="trabajador",
            periodicidad="por_evento",
            tipo_version=TipoVersion.CORRECCION,
            autor=self.prevencionista,
            motivo="Renombre ficticio",
        )
        migracion = importlib.import_module(
            "obligaciones.migrations.0004_versionobligacion_clasificacion_evidencia"
        )

        migracion.clasificar_examenes_existentes(
            apps,
            cast(BaseDatabaseSchemaEditor, None),
        )

        primera.refresh_from_db()
        renombrada.refresh_from_db()
        self.assertEqual(
            primera.clasificacion_evidencia,
            ClasificacionEvidencia.SALUD_OCUPACIONAL,
        )
        self.assertEqual(
            renombrada.clasificacion_evidencia,
            ClasificacionEvidencia.SALUD_OCUPACIONAL,
        )

    def test_bitacora_de_descarga_no_registra_datos_sensibles(self) -> None:
        self.client.force_login(self.prevencionista)
        respuesta = cast(
            FileResponse,
            self.client.get(
                reverse("evidencias:descargar", args=[self.evidencia.pk])
            ),
        )
        b"".join(cast(Iterable[bytes], respuesta.streaming_content))

        evento = EventoBitacora.objects.get(
            accion="descargar_evidencia",
            evidencia=self.evidencia,
        )
        self.assertNotIn(self.trabajador.nombre, evento.descripcion)
        self.assertNotIn(self.trabajador.rut, evento.descripcion)
        self.assertNotIn(self.evidencia.archivo.name, evento.descripcion)

    def test_recorrido_no_renderiza_datos_sensibles_ni_texto_historico(self) -> None:
        EventoBitacora.objects.create(
            actor=self.prevencionista,
            accion="acto_historico_sensible",
            entidad="Evidencia",
            identificador=str(self.evidencia.pk),
            descripcion=(
                f"Registro anterior para {self.trabajador.nombre} "
                f"({self.trabajador.rut}) en {self.evidencia.archivo.name}."
            ),
            canal="web",
            centro_costo=self.centro,
            obligacion=self.obligacion,
            evidencia=self.evidencia,
            trabajador=self.trabajador,
        )
        self.client.force_login(self.prevencionista)

        respuesta = self.client.get(
            reverse(
                "bitacora:recorrido",
                args=[self.centro.pk, self.obligacion.pk],
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "acto_historico_sensible")
        self.assertContains(respuesta, "Acto de salud ocupacional registrado")
        for dato_sensible in (
            self.trabajador.nombre,
            self.trabajador.rut,
            self.evidencia.archivo.name,
            self.evidencia.emisor,
        ):
            self.assertNotContains(respuesta, dato_sensible)

    def test_bitacora_de_operaciones_no_registra_datos_sensibles(self) -> None:
        CambioAplicabilidad.objects.create(
            trabajador=self.trabajador,
            obligacion=self.obligacion,
            aplica=True,
            motivo="Aplicabilidad ficticia para prueba",
            autor=self.prevencionista,
        )
        nombre_archivo = "Persona Reservada 12345678-5 control.pdf"
        evidencia_cargada = cargar_evidencia(
            centro=self.centro,
            obligacion=self.obligacion,
            trabajador=self.trabajador,
            actor=self.prevencionista,
            archivo=SimpleUploadedFile(nombre_archivo, b"otro contenido ficticio"),
            emisor="Prestador ficticio",
            fecha_emision=date(2026, 2, 1),
            fecha_vencimiento=date(2027, 2, 1),
        )
        corregir_evidencia(
            evidencia=evidencia_cargada,
            actor=self.prevencionista,
            fecha_emision=date(2026, 2, 2),
            fecha_vencimiento=date(2027, 2, 2),
            motivo="Corrección ficticia",
        )
        validar_evidencia(
            evidencia=evidencia_cargada,
            actor=self.prevencionista,
        )

        eventos = EventoBitacora.objects.filter(evidencia=evidencia_cargada)
        self.assertEqual(eventos.count(), 3)
        for evento in eventos:
            with self.subTest(accion=evento.accion):
                for dato_sensible in (
                    self.trabajador.nombre,
                    self.trabajador.rut,
                    nombre_archivo,
                    evidencia_cargada.archivo.name,
                ):
                    self.assertNotIn(dato_sensible, evento.descripcion)

    def test_registro_central_neutraliza_identificador_y_descripcion(self) -> None:
        evento = registrar_evento(
            actor=self.prevencionista,
            accion="acto_sensible_ficticio",
            entidad="plan de aplicación",
            identificador=self.trabajador.rut,
            descripcion=f"Acto para {self.trabajador.nombre} ({self.trabajador.rut}).",
            canal="web",
            contexto=ContextoBitacora.para_trabajador(
                self.trabajador,
                self.centro,
                self.obligacion,
            ),
        )

        self.assertEqual(evento.identificador, str(self.obligacion.pk))
        self.assertEqual(
            evento.descripcion,
            "Acto relacionado con salud ocupacional registrado.",
        )

    def test_migracion_sanea_evento_historico_sensible(self) -> None:
        evento = EventoBitacora.objects.create(
            actor=self.prevencionista,
            accion="acto_historico_sensible",
            entidad="plan de aplicación",
            identificador=self.trabajador.rut,
            descripcion=f"Acto para {self.trabajador.nombre} ({self.trabajador.rut}).",
            canal="web",
            centro_costo=self.centro,
            obligacion=self.obligacion,
            trabajador=self.trabajador,
        )
        migracion = importlib.import_module(
            "bitacora.migrations.0004_sanitizar_eventos_salud_ocupacional"
        )

        migracion.sanitizar_eventos_salud_ocupacional(
            apps,
            cast(BaseDatabaseSchemaEditor, None),
        )

        evento.refresh_from_db()
        self.assertEqual(evento.identificador, str(self.obligacion.pk))
        self.assertEqual(
            evento.descripcion,
            "Acto relacionado con salud ocupacional registrado.",
        )

    def test_rechazo_de_titular_no_revela_identidad_en_el_mensaje(self) -> None:
        otro_centro = CentroCosto.objects.create(
            codigo_contable="ADM-OTRO",
            nombre="Centro ficticio alternativo",
            tipo=CentroCosto.Tipo.CENTRO_ADMINISTRATIVO,
        )

        with self.assertRaises(ValidationError) as contexto:
            exigir_titular_coherente(
                version=self.version,
                centro=otro_centro,
                trabajador=self.trabajador,
            )

        mensaje = "; ".join(contexto.exception.messages)
        self.assertNotIn(self.trabajador.nombre, mensaje)
        self.assertNotIn(self.trabajador.rut, mensaje)

    def test_los_accesos_no_modifican_archivo_hash_ni_fechas(self) -> None:
        valores_originales = (
            self.evidencia.archivo.name,
            self.evidencia.hash_sha256,
            self.evidencia.fecha_emision,
            self.evidencia.fecha_vencimiento,
        )
        self.client.force_login(self.prevencionista)
        respuesta = cast(
            FileResponse,
            self.client.get(
                reverse("evidencias:descargar", args=[self.evidencia.pk])
            ),
        )
        self.assertEqual(
            b"".join(cast(Iterable[bytes], respuesta.streaming_content)),
            CONTENIDO,
        )

        self.evidencia.refresh_from_db()
        self.assertEqual(
            (
                self.evidencia.archivo.name,
                self.evidencia.hash_sha256,
                self.evidencia.fecha_emision,
                self.evidencia.fecha_vencimiento,
            ),
            valores_originales,
        )
