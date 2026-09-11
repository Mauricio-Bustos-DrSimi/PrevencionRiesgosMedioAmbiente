# 03: Sidebar y barra superior

**What to build:** Navegación lateral y barra superior que orienten al usuario y reflejen las capacidades existentes.

**Status:** completed

**Blocked by:** None

## Evidencia de cierre

- Captura de escritorio a 1366 × 768: `.desarrollo-local/ticket3-1366.png`.
- Captura de escritorio a 1920 × 1080: `.desarrollo-local/ticket3-1920.png`.
- Pruebas focalizadas: 15/15 aprobadas.
- `python manage.py check`: aprobado, sin problemas identificados.
- `mypy` sobre los archivos Python propios del ticket: aprobado, sin errores.
- `findstatic prevencion/img/logo-institucional.png`: aprobado; resolvió el logotipo desde `static/prevencion/img/logo-institucional.png`.
- `git diff --check`: aprobado, sin errores de espacios en blanco.

## Archivos a crear o modificar

- Crear `templates/includes/sidebar.html` y `templates/includes/topbar.html`.
- Crear `acceso/context_processors.py` y registrarlo si se requiere.
- Modificar `templates/layouts/aplicacion.html` y `configuracion/settings.py`.
- Usar el logotipo original solo si se localiza y autoriza; si no, texto accesible.

## Criterios de aceptación

- Sidebar visible en escritorio con Inicio, Operación, Gestión y Administración.
- Administración e importaciones se muestran según permisos existentes.
- La sección activa usa `aria-current`; planes y bitácora conservan acceso contextual.
- Topbar muestra logo o sustituto textual accesible, título, usuario, rol y `DEMOSTRACIÓN` solo con `DJANGO_ENTORNO=demo`.
- Prevencionista y Sysadmin conservan sus permisos; no se añaden permisos.

## Pruebas específicas

- `python manage.py check`.
- Pruebas HTTP para anónimo, usuario sin rol, Prevencionista, Sysadmin y superusuario sin grupo Prevencionista.
- Comprobación estática de rutas y capacidades.

## Comprobación visual manual

- Revisar sidebar, topbar, sección activa, logo/sustituto textual y foco a 1366 × 768 y 1920 × 1080.

## Riesgos de regresión

- Exponer enlaces no autorizados, confundir superusuario con Prevencionista o romper URLs.
