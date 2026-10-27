# 02: Protección de exámenes ocupacionales

**Status:** ready-for-agent

## Objetivo

Impedir que Encargado, Lector u otro usuario no autorizado consulte o descargue
evidencias clasificadas como información de salud ocupacional.

## Alcance

- Clasificación explícita de evidencias sensibles; no se infiere por el nombre.
- Acceso exclusivo de Prevencionista y Sysadmin a archivo y metadatos sensibles.
- Ocultamiento de enlaces y autorización obligatoria en el servidor.
- Cobertura de detalle, descarga, integridad, bitácora y resultados operativos.

## Dependencias

- 01: Descarga autenticada de evidencias.

## Archivos afectados

- `obligaciones/models.py`
- `obligaciones/admin.py`
- `obligaciones/migrations/` (nueva migración)
- `acceso/permisos.py`
- `evidencias/views.py`
- `bitacora/views.py`
- Plantillas que muestran evidencias o enlaces de descarga
- Pruebas HTTP de obligaciones, evidencias y bitácora

## Migraciones necesarias

Sí. Se necesita un atributo versionado que identifique la clasificación de la
evidencia y una migración de datos controlada para las cuatro obligaciones de
exámenes del catálogo de demostración.

## Riesgos de seguridad

- Exposición de datos de salud mediante enlaces, metadatos, bitácora o descarga.
- Autorizar por texto del nombre y perder protección al renombrar la obligación.
- Proteger la interfaz pero permitir la petición directa.

## Criterios de aceptación

- [ ] La sensibilidad forma parte de la versión de la obligación.
- [ ] Prevencionista y Sysadmin pueden consultar y descargar un examen.
- [ ] Encargado y Lector reciben 403 en todas las rutas sensibles.
- [ ] Las pantallas no muestran enlace, nombre de archivo ni metadatos médicos a roles denegados.
- [ ] Renombrar una obligación no cambia su clasificación.
- [ ] La bitácora conserva trazabilidad sin revelar contenido sensible.

## Motivo del bloqueo

No está bloqueado: la restricción a Prevencionista y Sysadmin ya está acordada y
no depende de normas ni periodicidades.
