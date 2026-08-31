# 08: Mostrar vencimientos y trabajo pendiente

**What to build:** El sistema deriva Por vencer y Vencido al avanzar el tiempo y ofrece al Prevencionista bandejas operativas para obligaciones vencidas, obligaciones por vencer y evidencias pendientes de validación.

**Blocked by:** 07: Validar evidencia y derivar el cumplimiento vigente.

**Status:** resolved

- [x] El umbral de Por vencer es configurable, se aplica uniformemente y puede ser consultado por el Departamento de Prevención de Riesgos.
- [x] Una evidencia validada cambia de Vigente a Por vencer al entrar en el umbral configurado.
- [x] Una evidencia validada cambia a Vencido cuando termina su vigencia.
- [x] Sin evidencia permanece distinguible de Vencido en cálculos, filtros y presentación.
- [x] La bandeja de vencimientos separa o filtra Vencido y Por vencer y permite abrir el caso correspondiente.
- [x] La bandeja de validación muestra evidencias Pendientes de validación y permite abrirlas.
- [x] Los estados cambian por el paso del tiempo sin escrituras manuales ni tareas que modifiquen un estado almacenado.
- [x] Las pruebas controlan el tiempo y comprueban las transiciones mediante respuestas HTTP observables.

## Answer

Implementado en los commits `ca361ef`, `f1897ed`, `05d6371` y `859519f`.

- El umbral uniforme de Por vencer se configura con `DIAS_POR_VENCER` y se muestra en la bandeja.
- Los estados Vigente, Por vencer, Vencido, Pendiente de validación y Sin evidencia se derivan al consultar, sin almacenar ni modificar manualmente el estado.
- La bandeja filtra por estado, tipo de centro de costo y obligación, y abre el centro, la obligación y la evidencia relacionada.
- La selección respeta la historia append-only: una evidencia nueva supersede a la anterior cuando comienza su vigencia, sin que una evidencia futura o una obligación cerrada genere trabajo incorrecto.
- La portada enlaza las bandejas de vencimientos y de validación.
- Verificación final: 39 pruebas, mypy sobre 74 archivos, Django check y control de migraciones sin errores; revisión de estándares y especificación sin hallazgos pendientes.
