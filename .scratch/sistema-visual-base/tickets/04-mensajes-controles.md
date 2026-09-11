# 04: Mensajes y controles compartidos

**What to build:** Mensajes globales, botones, filtros, tarjetas, formularios y tablas con una presentación accesible y consistente.

**Status:** ready-for-agent

**Blocked by:** None (ticket 3 completado)

## Archivos a crear o modificar

- Crear o completar `templates/includes/mensajes.html`, `tarjeta_kpi.html` y `evidencias/includes/filtros_operacion.html`.
- Modificar `templates/layouts/aplicacion.html` y CSS de componentes.

## Criterios de aceptación

- Mensajes escapados con roles accesibles y sin cierre dependiente de JavaScript.
- Formularios conservan etiquetas, errores, CSRF, POST y `multipart/form-data`.
- Filtros GET conservan parámetros, selección y enlace Limpiar.
- Tablas tienen caption, encabezados `scope` y desplazamiento interno.
- No se alteran nombres de campos ni validaciones.

## Pruebas específicas

- `python manage.py check`.
- Pruebas HTTP de mensajes, filtros, CSRF, multipart y estado vacío.
- Comprobación estática de roles ARIA y atributos de formulario.

## Comprobación visual manual

- Revisar mensajes largos, errores, filtros activos, controles y tablas anchas sin JavaScript.

## Riesgos de regresión

- Perder parámetros GET, romper carga de evidencia o provocar scroll horizontal global.
