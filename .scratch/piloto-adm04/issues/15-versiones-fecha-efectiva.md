# 15: Versiones de obligación con fecha efectiva

**Status:** ready-for-agent

## Objetivo

Aplicar una regla nueva desde su fecha efectiva, conservar la anterior hasta ese
momento y reconstruir el cumplimiento sin retroactividad.

## Alcance

- Fecha efectiva de cada versión y cierre explícito de la anterior.
- Consulta de la versión que regía en una fecha dada.
- Evidencias vinculadas a la versión que las exigió.
- Casos pendientes de adecuación al entrar en vigor una versión nueva.
- Prohibición de retroceder una versión aprobada a Borrador.

## Dependencias

- 12: Gobierno del catálogo y actas.

## Archivos afectados

- `obligaciones/models.py`
- Servicios de `obligaciones`, `planes_aplicacion` y `evidencias`
- Formularios, vistas y plantillas de catálogo e historial
- `bitacora/registro.py`
- Migraciones y pruebas temporales y de recorrido de aceptación

## Migraciones necesarias

Sí. Fecha efectiva y relaciones de cierre o sucesión append-only. La migración
de datos debe preservar el comportamiento histórico de las versiones existentes.

## Riesgos de seguridad

- Recalcular el pasado con la regla actual.
- Dos versiones operativas superpuestas sin resolución determinista.
- Editar una versión aprobada.
- Desvincular una evidencia de la versión original.

## Criterios de aceptación

- [ ] Una consulta histórica usa la versión vigente en la fecha consultada.
- [ ] La versión anterior rige hasta la fecha efectiva de la nueva.
- [ ] El cambio no crea incumplimientos anteriores a su fecha efectiva.
- [ ] Las evidencias conservan su versión original.
- [ ] Los casos que deben adaptarse se muestran sin alterar la historia.
- [ ] Corregir una regla crea Borrador nuevo y cierra la versión incorrecta.

## Motivo del bloqueo

No está bloqueado: el comportamiento temporal fue confirmado y puede probarse
con un reloj controlado y reglas ficticias.
