# 16: Aislamiento del entorno de demostración

**Status:** blocked-by-infrastructure

## Objetivo

Combinar barreras de aplicación e infraestructura para que ADM04 no comparta
base, medios, claves ni registros con producción y no pueda promocionarse por
error.

## Alcance

- Base, medios, clave y variables exclusivas.
- Etiqueta DEMOSTRACIÓN y validación del entorno en operaciones de siembra.
- Registros de demostración excluidos de alertas e indicadores operativos.
- Prohibición de recibir evidencia real o copiar registros a producción.
- Creación independiente en producción mediante acta, nunca promoción física.

## Dependencias

- Definir los recursos concretos de demo y producción.
- Definir la barrera técnica adicional a `DJANGO_ENTORNO=demo`.
- 12: Gobierno del catálogo y actas.
- 09 antes de verificar aislamiento respecto del PostgreSQL productivo.

## Archivos afectados

- `configuracion/settings.py`
- `acceso/context_processors.py`
- `importaciones/management/commands/sembrar_demo_bodega.py`
- Servicios de indicadores y evidencias
- `scripts/demo-local.ps1`
- Modelos o migraciones si se registra procedencia de entorno
- Pruebas de aislamiento y documentación operativa
- Configuración externa de base, medios y secretos

## Migraciones necesarias

Por determinar. Será necesaria si la barrera aprobada exige marcar la
procedencia de registros; no debe decidirse solo mediante una variable de entorno.

## Riesgos de seguridad

- Usar `DJANGO_ENTORNO` como única protección.
- Conectar demo a la base o medios productivos.
- Copiar evidencias personales o de salud al piloto.
- Convertir físicamente una versión demo en productiva.

## Criterios de aceptación

- [ ] Demo y producción tienen identificadores de base y rutas de medios diferentes.
- [ ] Claves y variables se administran por separado y fuera del repositorio.
- [ ] La aplicación rechaza una combinación de recursos incompatible con el entorno.
- [ ] Los registros demo no generan alertas ni KPI operativos.
- [ ] El piloto no acepta evidencia real.
- [ ] No existe una operación que promocione físicamente registros demo.
- [ ] Una prueba de configuración demuestra que cambiar solo la etiqueta no elimina las demás barreras.

## Motivo del bloqueo

Faltan los recursos de infraestructura y la decisión sobre la barrera técnica
adicional que distinguirá los entornos. No puede resolverse solo desde el código.
