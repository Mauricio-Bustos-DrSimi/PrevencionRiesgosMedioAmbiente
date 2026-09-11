# 02: Base HTML y layout de aplicación

**What to build:** Una herencia de templates que entregue un documento accesible y un layout operativo común.

**Status:** ready-for-agent

**Blocked by:** None (ticket 1 implementado técnicamente)

## Archivos a crear o modificar

- Crear `templates/base.html` y `templates/layouts/aplicacion.html`.
- Crear `templates/includes/estado_cumplimiento.html` y `estado_vacio.html`.
- Migrar solo una plantilla mínima de prueba al layout; no migrar todavía portada u operación.

## Criterios de aceptación

- `base.html` define idioma español, UTF-8, viewport, título, estilos y “Saltar al contenido”.
- `aplicacion.html` tiene sidebar/topbar como puntos de extensión, un solo `main` y bloques de título, acciones y contenido.
- Los includes no generan HTML duplicado.
- Funciona sin JavaScript y no cambia URLs, permisos ni formularios.

## Pruebas específicas

- `python manage.py check`.
- Prueba HTTP de una plantilla heredada, landmarks y un único `h1`.
- Comprobación estática de bloques y ausencia de scripts obligatorios.

## Comprobación visual manual

- Renderizar la plantilla mínima en ambas resoluciones y revisar ancho, fondo, foco y desplazamiento.

## Riesgos de regresión

- Bloques mal nombrados, HTML anidado o pérdida de mensajes/CSRF al migrar.
