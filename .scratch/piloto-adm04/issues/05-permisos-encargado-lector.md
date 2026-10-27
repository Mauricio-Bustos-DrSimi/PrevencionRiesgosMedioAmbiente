# 05: Permisos de Administrador, Prevencionista y Encargado

**Status:** completed

> Estas reglas fueron confirmadas por el responsable del proyecto para el MVP.
> No requieren un acta, Excel ni entrevista adicional para implementarse.

## Objetivo

Aplicar autorización por rol y por centro de costo para que Administrador y
Prevencionista mantengan alcance global, y Encargado consulte exclusivamente su
centro asignado y vigente.

## Alcance

- Matriz explícita de vistas y acciones para Administrador, Prevencionista y
  Encargado.
- Asociación histórica o vigente entre Encargado y centro de costo.
- Controles de objeto en el servidor, además del ocultamiento visual.
- Encargado solo consulta su centro; no modifica planes, obligaciones,
  trabajadores ni evidencias, no importa, no administra y no descarga archivos.
- Exámenes ocupacionales restringidos a Administrador y Prevencionista.
- Lector, externos y franquicias quedan fuera de esta implementación.

## Dependencias

- 01: Descarga autenticada de evidencias.
- 02: Protección de exámenes ocupacionales.
- Decisiones del responsable del proyecto confirmadas para el MVP.

## Archivos afectados

- `acceso/permisos.py`
- `acceso/context_processors.py`
- `acceso/migrations/` y posibles modelos de asignación de centro
- Vistas de `centros_costo`, `trabajadores`, `planes_aplicacion`, `evidencias`, `obligaciones`, `importaciones` y `bitacora`
- Sidebar, topbar y plantillas operativas
- Pruebas HTTP de permisos por aplicación

## Migraciones necesarias

Sí: grupo canónico Encargado y una relación histórica entre el Encargado y sus
centros autorizados. Sysadmin conserva su equivalencia técnica con Administrador.

## Riesgos de seguridad

- Acceso horizontal a otro centro cambiando un identificador en la URL.
- Exposición de RUT completos, exámenes o archivos a un rol de alcance reducido.
- Confiar en botones ocultos sin autorización en el servidor.
- Permitir que Encargado ejecute mutaciones mediante peticiones directas.

## Criterios de aceptación

- [x] Existe una decisión aprobada de rol y alcance para el MVP.
- [x] Encargado no puede consultar ni modificar otro centro de costo.
- [x] Encargado no puede ejecutar mutaciones, importar ni administrar.
- [x] Prevencionista y Administrador conservan alcance global y las capacidades
  confirmadas para el MVP; Sysadmin es su equivalente técnico.
- [x] Las peticiones directas incumpliendo la matriz reciben 403.
- [x] Los exámenes ocupacionales permanecen restringidos.

## Evidencia de implementación

- Migración `acceso.0002_asignacion_encargado_centro`: grupo Encargado e
  historial inmutable de asignaciones y revocaciones.
- Autorización central en `acceso/permisos.py`, aplicada en vistas y servicios.
- Pruebas focalizadas: 101 aprobadas, incluida alteración de IDs, privacidad de
  exámenes, lectura por centro y capacidades globales.
- `manage.py check`: sin observaciones.
- `mypy` focalizado: sin observaciones.
- Migración aplicada solo en la base local aislada de demostración.

## Motivo del bloqueo

Sin bloqueo de negocio. El responsable del proyecto confirmó el modelo para el
MVP. Lector no forma parte de esta implementación.
