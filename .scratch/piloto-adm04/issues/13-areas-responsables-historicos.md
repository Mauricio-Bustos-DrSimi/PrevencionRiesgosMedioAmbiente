# 13: Áreas y responsables históricos

**Status:** ready-for-agent

## Objetivo

Asignar a cada obligación un área controlada, responsable titular y reemplazante,
con vigencia e historia completa de los cambios.

## Alcance

- Catálogo Sysadmin con las siete áreas aprobadas.
- Asignación desde el detalle de la obligación.
- Titular y reemplazante seleccionados entre usuarios activos.
- Fecha de inicio, motivo, actor y cierre de la asignación anterior.
- Registro explícito cuando el reemplazante actúa.

## Dependencias

- 12: Gobierno del catálogo y actas.

## Archivos afectados

- `obligaciones/models.py`
- `obligaciones/forms.py`
- `obligaciones/views.py`
- `obligaciones/admin.py`
- Plantillas de detalle de obligación
- `acceso/permisos.py`
- `bitacora/registro.py`
- Migraciones y pruebas de obligaciones, permisos y trazabilidad

## Migraciones necesarias

Sí. Catálogo de áreas y asignaciones append-only con área, titular,
reemplazante, vigencia, motivo y actor.

## Riesgos de seguridad

- Asignar responsables mediante una petición directa sin ser Sysadmin.
- Conceder grupos o permisos como efecto secundario.
- Perder historia al desactivar un usuario o área.
- Confundir al actor técnico con la autoridad de negocio.

## Criterios de aceptación

- [ ] Existen exactamente las siete áreas iniciales aprobadas, sin variantes duplicadas.
- [ ] Solo Sysadmin ve y ejecuta Asignar responsables.
- [ ] El servidor rechaza la petición directa de otro rol.
- [ ] Cambiar responsables cierra la asignación anterior y conserva la historia.
- [ ] Desactivar usuarios o áreas no elimina registros históricos.
- [ ] La asignación no modifica grupos ni permisos.
- [ ] La actuación del reemplazante queda identificada como tal.

## Motivo del bloqueo

No está bloqueado: el catálogo y comportamiento están definidos. Las personas
concretas se cargarán después como datos y no son necesarias para implementar.
