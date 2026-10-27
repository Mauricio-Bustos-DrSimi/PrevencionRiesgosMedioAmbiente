# 01: Descarga autenticada de evidencias

**Status:** ready-for-agent

## Objetivo

Permitir que un usuario autorizado descargue una evidencia mediante una vista
Django protegida, sin exponer el archivo directamente bajo `MEDIA_URL`.

## Alcance

- Ruta de descarga por identificador de evidencia.
- Autenticación y autorización en el servidor antes de abrir el archivo.
- Respuesta como adjunto, con nombre seguro y tipo de contenido controlado.
- Enlaces desde el detalle y la trazabilidad.
- Registro de la descarga en la bitácora.

## Dependencias

Ninguna. Puede comenzar inmediatamente.

## Archivos afectados

- `evidencias/views.py`
- `evidencias/urls.py`
- `templates/evidencias/validar.html`
- `templates/bitacora/recorrido.html`
- `evidencias/tests/test_descarga_http.py` (nuevo)
- `bitacora/tests/test_trazabilidad_http.py`

## Migraciones necesarias

Ninguna.

## Riesgos de seguridad

- Acceso directo a archivos mediante una URL predecible.
- Traversal o divulgación de la ruta física del servidor.
- Descarga por un usuario autenticado sin autorización sobre la evidencia.
- Interpretación activa del contenido en el navegador.

## Criterios de aceptación

- [ ] Un usuario anónimo es redirigido al inicio de sesión.
- [ ] Un usuario sin autorización recibe 403 aunque conozca el identificador.
- [ ] Un operador autorizado obtiene exactamente los bytes almacenados.
- [ ] La respuesta fuerza descarga, no revela rutas locales y usa un nombre seguro.
- [ ] Un identificador inexistente responde 404 sin filtrar información.
- [ ] La descarga queda registrada con actor, evidencia y fecha en la bitácora.
- [ ] Ninguna plantilla enlaza directamente a `evidencia.archivo.url`.

## Motivo del bloqueo

No está bloqueado: no depende de normas ni periodicidades.
