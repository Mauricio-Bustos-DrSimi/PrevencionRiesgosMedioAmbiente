# 03: Cierre de sesión

**Status:** ready-for-agent

## Objetivo

Permitir que cualquier usuario autenticado cierre su sesión de forma explícita y
segura desde la barra superior.

## Alcance

- Ruta de cierre de sesión mediante POST.
- Formulario con CSRF en la barra superior.
- Invalidación de sesión y redirección al inicio de sesión.
- Funcionamiento sin JavaScript.

## Dependencias

Ninguna. Puede comenzar inmediatamente.

## Archivos afectados

- `configuracion/urls.py`
- `templates/includes/topbar.html`
- `acceso/tests/test_navegacion_visual.py`
- Prueba HTTP específica de autenticación

## Migraciones necesarias

Ninguna.

## Riesgos de seguridad

- Cierre mediante GET susceptible de activación involuntaria.
- Formulario sin CSRF.
- Sesión que continúe válida después de la respuesta.

## Criterios de aceptación

- [ ] La barra superior muestra Cerrar sesión a usuarios autenticados.
- [ ] GET no cierra la sesión.
- [ ] POST sin CSRF es rechazado.
- [ ] POST válido invalida la sesión y redirige al inicio de sesión.
- [ ] El control funciona con JavaScript deshabilitado y mediante teclado.

## Motivo del bloqueo

No está bloqueado: no depende de reglas de negocio del catálogo.
