# 07: Validar evidencia y derivar el cumplimiento vigente

**What to build:** Un Prevencionista puede confirmar que una evidencia corresponde a su obligación y que sus fechas son correctas. Solo entonces el sistema deriva Vigente desde la periodicidad y la vigencia, sin ofrecer una forma de ingresar manualmente el estado de cumplimiento.

**Blocked by:** 06: Cargar evidencia pendiente con integridad verificable.

**Status:** resolved

- [x] La bandeja de validación permite abrir una evidencia Pendiente de validación con el contexto de su centro de costo y obligación.
- [x] Validar una evidencia exige una identidad Prevencionista autorizada y conserva quién y cuándo realizó la validación.
- [x] Una evidencia validada dentro de su vigencia produce el estado de cumplimiento Vigente.
- [x] La vigencia se deriva usando la periodicidad de la obligación y las fechas de la evidencia.
- [x] El estado de cumplimiento no puede ser ingresado ni cambiado manualmente desde las pantallas propias o el panel administrativo.
- [x] Una evidencia que continúa pendiente cuenta como no cumplida.
- [x] La validación agrega un acto a la bitácora del dominio.
- [x] Una prueba HTTP recorre carga, estado Pendiente de validación, validación y estado Vigente.

## Answer

Implementado en los commits `6057cbd`, `c387052`, `1bbf1cd`, `dbeb849` y `1c3a91e`.

- La bandeja y el detalle permiten revisar y validar evidencias pendientes mediante HTTP.
- La validación es un acto append-only con identidad, fecha y entrada en la bitácora.
- La vigencia usa la periodicidad y la versión de obligación preservada al cargar la evidencia.
- El estado de validación y el cumplimiento Vigente se derivan; no existe un campo editable de estado.
- Verificación final: 32 pruebas y mypy sobre 73 archivos, sin errores.
