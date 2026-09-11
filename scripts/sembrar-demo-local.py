"""Semilla completamente ficticia; ejecutar mediante demo-local.ps1 Sembrar."""

import secrets
from datetime import timedelta
from pathlib import Path

import django

django.setup()

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.utils import timezone

from centros_costo.models import CentroCosto
from evidencias.services import cargar_evidencia, validar_evidencia
from importaciones.pdf import marcador_pdf
from obligaciones.models import Obligacion, VersionObligacion
from planes_aplicacion.models import CambioAplicabilidad
from trabajadores.services import crear_trabajador, validar_trabajador

base = settings.DATABASES['default']
esperado = Path(settings.BASE_DIR) / '.desarrollo-local' / 'demo-mvp'
if (base['NAME'], base['HOST'], str(base['PORT'])) != (
    'prevencion_desarrollo_demo', '127.0.0.1', '55433'
):
    raise RuntimeError('La semilla solo admite la base de desarrollo local.')
if Path(settings.MEDIA_ROOT).resolve() != (esperado / 'medios-demo').resolve():
    raise RuntimeError('Directorio de medios no aislado.')
with connection.cursor() as cursor:
    cursor.execute('SHOW data_directory')
    if Path(cursor.fetchone()[0]).resolve() != (esperado / 'postgres').resolve():
        raise RuntimeError('Cluster distinto al de la demo.')

clave = secrets.token_urlsafe(18)
hoy = timezone.localdate()
with transaction.atomic():
    if User.objects.exists() or CentroCosto.objects.exists() or Obligacion.objects.exists():
        raise RuntimeError('La semilla requiere una base sin usuarios ni datos de dominio.')
    actor = User.objects.create_superuser('demo_mvp', 'demo@example.invalid', clave)
    actor.groups.add(Group.objects.get(name='Prevencionista'))
    centro = CentroCosto.objects.create(
        codigo_contable='DEMO-BODEGA-001', nombre='Bodega ficticia - DEMOSTRACION', tipo='bodega'
    )
    for nombre, dias, validar in [
        ('Documento ficticio vigente', 180, True),
        ('Documento ficticio por vencer', 10, True),
        ('Documento ficticio vencido', -10, True),
        ('Documento ficticio pendiente de validacion', 180, False),
        ('Obligacion ficticia sin evidencia', None, False),
        ('Obligacion ficticia no aplicable', None, False),
    ]:
        obligacion = Obligacion.objects.create()
        VersionObligacion.objects.create(
            obligacion=obligacion, numero=1, nombre=nombre,
            norma_origen='FICTICIA - sin valor normativo', titular='centro_costo',
            periodicidad='anual', tipo_version='alta', autor=actor, motivo='Demostracion ficticia'
        )
        CambioAplicabilidad.objects.create(
            centro_costo=centro, obligacion=obligacion,
            aplica='no aplicable' not in nombre, autor=actor, motivo='Demostracion ficticia'
        )
        if dias is not None:
            contenido = marcador_pdf(['DEMO - DOCUMENTO FICTICIO', nombre, 'SIN VALOR LEGAL'])
            evidencia = cargar_evidencia(
                centro=centro, obligacion=obligacion, actor=actor,
                archivo=SimpleUploadedFile('documento-ficticio.pdf', contenido, content_type='application/pdf'),
                emisor='Emisor ficticio', fecha_emision=hoy-timedelta(days=30),
                fecha_vencimiento=hoy+timedelta(days=dias), canal='demo_local'
            )
            if validar:
                validar_evidencia(evidencia=evidencia, actor=actor, canal='demo_local')
    trabajador = crear_trabajador(
        rut='11111111-1', nombre='Persona Ficticia DEMO UNO', cargo='Cargo ficticio',
        centro=centro, motivo='Identidad sintetica de demostracion', actor=actor, canal='demo_local'
    )
    validar_trabajador(trabajador=trabajador, actor=actor, canal='demo_local')
print('Usuario local: demo_mvp')
print('Clave local: ' + clave)
print('Creada bodega ficticia con 6 obligaciones, 4 PDF sinteticos y 1 trabajador ficticio.')
