# 10: Respaldo conjunto de base y evidencias

**Status:** blocked-by-infrastructure

## Objetivo

Respaldar y restaurar PostgreSQL y los archivos de evidencia como una unidad
consistente, preservando relaciones, hashes e historia append-only.

## Alcance

- Procedimiento coordinado de respaldo de base y almacenamiento de evidencias.
- Identificador común, hora, inventario y resultado verificable por ejecución.
- Cifrado, retención, acceso restringido y copia fuera del servidor principal.
- Prueba periódica de restauración aislada y verificación de hashes.

## Dependencias

- 09: PostgreSQL productivo.
- Almacenamiento definitivo de evidencias.
- Destino de respaldo, retención, RPO, RTO y responsable operativo aprobados.

## Archivos afectados

- Scripts versionados de respaldo y restauración, por crear
- Documentación o runbook operativo, por crear
- Configuración externa del programador, almacenamiento y secretos
- Pruebas o comprobadores de restauración, por crear

## Migraciones necesarias

Ninguna.

## Riesgos de seguridad

- Respaldo de base y archivos tomado en momentos incompatibles.
- Copias sin cifrar de documentos personales o de salud.
- Restauración no probada o pérdida silenciosa de archivos.
- Secretos incluidos en scripts, logs o artefactos.

## Criterios de aceptación

- [ ] Cada respaldo vincula dump, conjunto de archivos, fecha e inventario.
- [ ] El proceso detecta archivos faltantes y fallos parciales.
- [ ] Las copias están cifradas y limitadas a operadores autorizados.
- [ ] Una restauración aislada recupera base y medios sin usar producción.
- [ ] La comprobación posterior valida una muestra definida o el total de hashes.
- [ ] RPO, RTO, retención y calendario de pruebas están aprobados.

## Motivo del bloqueo

No están definidos el PostgreSQL productivo, almacenamiento, destino de respaldo,
retención ni objetivos de recuperación.
