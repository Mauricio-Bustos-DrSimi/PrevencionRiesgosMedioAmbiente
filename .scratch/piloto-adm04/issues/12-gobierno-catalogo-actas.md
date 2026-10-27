# 12: Gobierno del catálogo y actas de aprobación

**Status:** ready-for-agent

## Objetivo

Gestionar el estado administrativo de cada versión de obligación y registrar el
acto formal que permite aprobarla, sin confundirlo con la validación de evidencia.

## Alcance

- Estados Borrador, Validada para demostración, Aprobada para operación y Cerrada.
- Transiciones append-only ejecutadas solo por Sysadmin.
- Acta con identificador, fecha, versión, fuente, responsable titular,
  participantes, decisión, observaciones y archivo o enlace.
- Registro separado del responsable de negocio y del usuario ejecutor.

## Dependencias

Ninguna. Las reglas de transición y campos obligatorios están confirmados.

## Archivos afectados

- `obligaciones/models.py`
- `obligaciones/forms.py`
- `obligaciones/views.py`
- `obligaciones/urls.py`
- `obligaciones/admin.py`
- Plantillas de catálogo y detalle de obligación
- `bitacora/registro.py`
- Migraciones y pruebas de obligaciones y trazabilidad

## Migraciones necesarias

Sí. Nuevos registros append-only para transiciones y actas, asociados a una
versión de obligación y protegidos contra modificación o eliminación.

## Riesgos de seguridad

- Que Sysadmin sustituya la aprobación del responsable titular.
- Aprobar sin fuente, motivo o acta.
- Editar o borrar una transición anterior.
- Crear Aprobada para operación en un entorno de demostración.

## Criterios de aceptación

- [ ] Solo Sysadmin puede registrar una transición y el servidor lo comprueba.
- [ ] Una aprobación operativa exige todos los campos definidos en la especificación.
- [ ] Responsable titular y usuario ejecutor se guardan por separado, aunque sean la misma persona.
- [ ] Las transiciones y actas no pueden editarse ni borrarse.
- [ ] Una corrección normativa crea una versión Borrador nueva.
- [ ] Una versión demo no se transforma en un registro productivo.

## Motivo del bloqueo

No está bloqueado: el flujo administrativo y el contenido del acta están
confirmados y pueden implementarse con datos ficticios.
