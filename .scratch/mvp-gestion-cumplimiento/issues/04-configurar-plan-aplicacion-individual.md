# 04: Configurar el plan de aplicación individual

**What to build:** Un Prevencionista puede partir de una sugerencia basada en el tipo de centro de costo y confirmar un plan de aplicación propio para cada instalación. La consulta debe distinguir Sin evidencia de No aplica y conservar cada cambio de aplicabilidad con autor, fecha y motivo.

**Blocked by:** 02: Registrar y consultar centros de costo; 03: Administrar el catálogo versionado de obligaciones.

**Status:** resolved

- [x] Un Prevencionista puede generar una sugerencia inicial de obligaciones a partir del tipo de centro de costo.
- [x] La sugerencia no se convierte en herencia: el plan queda confirmado y administrado individualmente para cada centro de costo.
- [x] Un Prevencionista puede agregar una obligación al plan de aplicación o declarar que No aplica.
- [x] Todo cambio de aplicabilidad exige motivo y conserva autor y fecha.
- [x] Una obligación aplicable sin evidencia muestra Sin evidencia.
- [x] Una obligación excluida del plan vigente muestra No aplica y no se presenta como incumplimiento.
- [x] La consulta permite reconstruir el plan de aplicación que existía en una fecha pasada.
- [x] Las pruebas recorren la configuración y consulta mediante interfaces públicas de Django.


## Answer

Implementado en el commit `db97015`.

La sugerencia por tipo de centro de costo es punto de partida, no herencia: el
plan queda confirmado y administrado individualmente. Todo cambio de
aplicabilidad exige motivo y conserva autor y fecha, lo que permite reconstruir
el plan vigente en una fecha pasada. Sin evidencia y No aplica permanecen
distinguibles.
