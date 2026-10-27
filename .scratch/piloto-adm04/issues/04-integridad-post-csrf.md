# 04: Verificación de integridad mediante POST con CSRF

**Status:** ready-for-agent

## Objetivo

Evitar que una navegación GET ejecute la lectura completa del archivo y registre
una acción; la verificación de integridad debe iniciarse mediante POST con CSRF.

## Alcance

- GET presenta una confirmación sin calcular el hash ni escribir en bitácora.
- POST autorizado calcula SHA-256, compara el resultado y registra el evento.
- Formulario accesible y funcional sin JavaScript.

## Dependencias

Ninguna. Debe reutilizar la autorización existente y ser compatible con el
ticket 02 cuando se implemente.

## Archivos afectados

- `evidencias/views.py`
- `templates/evidencias/integridad.html`
- `templates/bitacora/recorrido.html`
- `bitacora/tests/test_trazabilidad_http.py`
- Pruebas HTTP de evidencias

## Migraciones necesarias

Ninguna.

## Riesgos de seguridad

- CSRF que provoque lecturas costosas y eventos falsos.
- Denegación de servicio por verificaciones repetidas.
- Divulgación del resultado a usuarios sin acceso a la evidencia.

## Criterios de aceptación

- [ ] GET no abre el archivo, no calcula hash y no crea un evento.
- [ ] POST sin CSRF es rechazado.
- [ ] POST autorizado muestra hash registrado, calculado y resultado.
- [ ] Cada ejecución válida crea exactamente un evento de bitácora.
- [ ] Un usuario no autorizado recibe 403 antes de abrir el archivo.
- [ ] El flujo funciona sin JavaScript.

## Motivo del bloqueo

No está bloqueado: no depende de normas ni periodicidades.
