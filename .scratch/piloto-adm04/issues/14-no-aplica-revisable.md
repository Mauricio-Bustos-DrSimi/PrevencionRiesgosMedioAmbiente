# 14: Decisión No aplica revisable

**Status:** ready-for-agent

## Objetivo

Convertir No aplica en una decisión justificada, temporal y reactivable, con
evidencia e historia, en lugar de una exclusión permanente.

## Alcance

- Motivo, condición evaluada, evidencia justificativa, Prevencionista y fecha.
- Próxima revisión anual y reactivación manual ante los cambios acordados.
- Bandeja de casos próximos a revisión.
- Historial append-only de decisiones y reactivaciones.
- Uso restringido a demostración hasta completar esta capacidad.

## Dependencias

- 12: Gobierno del catálogo y actas.
- 01 y 02 para descargar y proteger la evidencia justificativa según su clasificación.

## Archivos afectados

- `planes_aplicacion/models.py`
- `planes_aplicacion/forms.py`
- `planes_aplicacion/services.py`
- `planes_aplicacion/views.py`
- `planes_aplicacion/urls.py`
- Plantillas de plan, motivo, operación y vencimientos
- `bitacora/registro.py`
- Migraciones y pruebas de planes, bandejas y trazabilidad

## Migraciones necesarias

Sí. Registro append-only de la decisión, próxima revisión y evidencia
justificativa, preservando los cambios de aplicabilidad existentes.

## Riesgos de seguridad

- No aplica sin evidencia o responsable.
- Exclusión indefinida que oculte un incumplimiento.
- Archivo justificativo accesible a un rol indebido.
- Sobrescribir la decisión anterior al reactivar.

## Criterios de aceptación

- [ ] No aplica exige todos los antecedentes confirmados en la especificación.
- [ ] La próxima revisión anual es obligatoria.
- [ ] Los casos próximos a revisión aparecen en una bandeja accionable.
- [ ] Una reactivación conserva la decisión anterior y su evidencia.
- [ ] Cambios de proceso, riesgo, equipo, dotación o instalación permiten registrar una reevaluación.
- [ ] Cada acto queda en la bitácora con su usuario concreto.

## Motivo del bloqueo

No está bloqueado: los datos y eventos obligatorios ya fueron confirmados. Puede
implementarse y probarse con archivos ficticios.
