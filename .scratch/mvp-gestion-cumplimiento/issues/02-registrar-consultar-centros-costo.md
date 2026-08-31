# 02: Registrar y consultar centros de costo

**What to build:** Un Sysadmin puede registrar centros de costo y un Prevencionista puede consultar las instalaciones incluidas en el piloto mediante su código contable oficial, tipo y referencia cruzada opcional. La exclusión de franquicias debe ser explícita y los cambios deben quedar en la bitácora del dominio.

**Blocked by:** 01: Iniciar la operación segura del MVP.

**Status:** resolved

- [x] Un Sysadmin puede registrar farmacias, centros administrativos y bodegas mediante el panel administrativo.
- [x] El código contable oficial identifica de manera única cada centro de costo.
- [x] `CveUnidad` se conserva como referencia cruzada opcional y no reemplaza al código contable oficial.
- [x] Las franquicias quedan excluidas mediante un dato explícito y no aparecen entre los centros de costo operables del piloto.
- [x] Un Prevencionista puede consultar y abrir el detalle de todos los centros de costo incluidos en el piloto.
- [x] Crear o cambiar un centro de costo registra qué ocurrió, quién actuó, cómo y cuándo en la bitácora del dominio.
- [x] Las pruebas verifican el comportamiento desde el panel administrativo y la consulta HTTP, sin depender de detalles internos del modelo.


## Answer

Implementado en el commit `009bdfe`, junto con el ticket 03.

El código contable oficial identifica de manera única cada centro de costo y
`CveUnidad` se conserva solo como referencia cruzada opcional. Las franquicias se
excluyen mediante el dato explícito `es_franquicia` y no aparecen entre los
centros operables. Altas y cambios quedan en la bitácora del dominio.
