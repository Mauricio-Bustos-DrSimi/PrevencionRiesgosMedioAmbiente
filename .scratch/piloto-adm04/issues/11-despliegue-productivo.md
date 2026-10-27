# 11: Despliegue productivo

**Status:** blocked-by-infrastructure

## Objetivo

Ejecutar la aplicación en un servicio productivo endurecido, observable y
recuperable, sin datos ni reglas de ADM04.

## Alcance

- Servicio WSGI/ASGI administrado y proxy HTTPS.
- Variables y clave exclusivas de producción.
- Archivos estáticos y evidencias fuera del código fuente.
- Verificaciones de despliegue, salud, logs, reinicio y reversión.
- Admin y rutas operativas protegidos.

## Dependencias

- 01–04: controles de descarga, salud, sesión e integridad.
- 09: PostgreSQL productivo.
- 10: respaldo conjunto probado.
- 12–16: gobierno, responsables, No aplica, versionado y separación de entornos.
- 05 solo antes de habilitar Encargado o Lector.

Los tickets 06–08 no despliegan ADM04 a producción: sus registros de
demostración permanecen separados.

## Archivos afectados

- `configuracion/settings.py`
- `configuracion/wsgi.py` o `configuracion/asgi.py`
- Dependencias y archivos de servicio/despliegue que se definan
- Archivo de variables de ejemplo, sin secretos
- Runbook de despliegue, reversión y operación
- Configuración externa de proxy, TLS, servicio y observabilidad

## Migraciones necesarias

No crea migraciones propias. Debe aplicar de forma controlada las migraciones
versionadas sobre la base nueva, con respaldo y plan de reversión.

## Riesgos de seguridad

- `DEBUG` activo, hosts abiertos, cookies inseguras o tráfico sin TLS.
- Servir evidencias directamente desde el proxy sin autorización Django.
- Compartir secretos o recursos con demo.
- Desplegar registros de ADM04 o ejecutar su siembra accidentalmente.

## Criterios de aceptación

- [ ] `manage.py check --deploy` no presenta hallazgos críticos.
- [ ] HTTPS, cookies seguras, hosts y orígenes CSRF están restringidos.
- [ ] Las evidencias solo salen por la descarga autenticada.
- [ ] Base, medios, clave y variables no se comparten con demo.
- [ ] ADM04 y sus evidencias no existen en producción.
- [ ] Reinicio, logs, monitoreo, respaldo y reversión están probados.
- [ ] La aplicación conserva admin, permisos y trazabilidad.

## Motivo del bloqueo

Faltan servidor, dominio, TLS, proceso de aplicación, almacenamiento, secretos,
PostgreSQL, monitoreo y responsables de operación.
