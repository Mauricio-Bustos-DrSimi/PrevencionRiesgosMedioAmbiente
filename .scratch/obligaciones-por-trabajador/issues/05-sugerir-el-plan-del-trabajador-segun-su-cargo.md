# 05: Sugerir el plan del trabajador según su cargo

**What to build:** Que dar de alta a alguien como *Operador de maquinaria* proponga de entrada las obligaciones que a ese cargo le corresponden —licencia de conducir, examen de operadores, manejo de extintores— en vez de armar el plan de 129 personas obligación por obligación. La sugerencia acelera; no decide: la aplicabilidad se sigue confirmando persona por persona.

Es el espejo de lo que ya existe para el centro de costo, donde el tipo sugiere y el Prevencionista confirma.

**Blocked by:** 03

**Type:** task

**Status:** resolved

- [x] La versión de obligación admite cargos sugeridos, con la misma semántica que los tipos de centro: vacío significa todos.
- [x] Un trabajador recibe una sugerencia de obligaciones de titular trabajador, filtrada por su cargo.
- [x] La sugerencia del centro de costo mantiene su filtro por titular centro de costo, sin cambios de comportamiento.
- [x] La aplicabilidad no se hereda automáticamente del cargo: el plan se confirma individualmente y queda registrado con autor, fecha y motivo.
- [x] Cambiar el cargo de un trabajador no modifica por sí solo su plan ya confirmado.
- [x] El plan de un trabajador se puede reconstruir a una fecha pasada.
- [x] Una obligación excluida del plan del trabajador produce **No aplica** para esa persona, no un incumplimiento.
- [x] Los seis cargos del respaldo de ADM04 quedan cubiertos por las pruebas.
