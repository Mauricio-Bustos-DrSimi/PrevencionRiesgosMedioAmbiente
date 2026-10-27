# 09: PostgreSQL productivo

**Status:** blocked-by-infrastructure

## Objetivo

Proveer una base PostgreSQL dedicada, endurecida y operable para la aplicación
productiva, separada de desarrollo, pruebas y ADM04.

## Alcance

- Instancia o base dedicada, usuario de mínimo privilegio y red restringida.
- Credenciales entregadas mediante secretos del entorno.
- Cifrado de conexión cuando la infraestructura lo permita.
- Monitoreo básico, capacidad, retención y procedimiento de migración.
- Prueba de conexión sin cargar datos del piloto.

## Dependencias

- Servidor o servicio PostgreSQL aprobado.
- Red, DNS, almacenamiento, secretos y responsables operativos definidos.

## Archivos afectados

- `configuracion/settings.py`, solo si se requieren opciones de conexión adicionales
- Archivo de ejemplo de variables, sin secretos
- Documentación operativa y scripts de comprobación que se acuerden
- Configuración externa del servidor PostgreSQL

## Migraciones necesarias

No crea migraciones de esquema. En la habilitación se aplicarán únicamente las
migraciones versionadas del proyecto sobre una base nueva y vacía.

## Riesgos de seguridad

- Credenciales en el repositorio o comandos registrados.
- Acceso de red excesivo o usuario propietario innecesario.
- Confundir bases de demo, prueba y producción.
- Aplicar migraciones sobre una base existente no identificada.

## Criterios de aceptación

- [ ] Nombre, host, puerto y propietario operativo están documentados.
- [ ] La base es nueva, dedicada y distinta de ADM04 y pruebas.
- [ ] La aplicación usa un usuario de mínimo privilegio y secretos externos.
- [ ] El acceso de red está limitado a los componentes autorizados.
- [ ] La conexión y `manage.py check --deploy` se validan sin sembrar ADM04.
- [ ] Existe evidencia de capacidad, monitoreo y responsable de incidentes.

## Motivo del bloqueo

Faltan servidor, red, credenciales, almacenamiento y decisiones operativas de
producción. No pueden inferirse desde el repositorio.
