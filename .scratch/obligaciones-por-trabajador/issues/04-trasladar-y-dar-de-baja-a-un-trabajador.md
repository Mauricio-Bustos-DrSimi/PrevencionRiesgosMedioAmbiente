# 04: Trasladar y dar de baja a un trabajador

**What to build:** Que Prevención mueva a una persona de un centro de costo a otro, o la dé de baja al egreso, sin perder nada de lo que se acreditó mientras estuvo donde estaba, y que la consulta a una fecha pasada use la dotación que existía entonces y no la de hoy.

**Blocked by:** 03

**Type:** task

**Status:** resolved

- [x] Un Prevencionista puede trasladar un trabajador a otro centro de costo, indicando fecha y motivo.
- [x] Solo Prevención traslada o da de baja; el Encargado no puede hacerlo cuando exista ese rol.
- [x] La baja es un cierre append-only con motivo, no un borrado.
- [x] La evidencia cargada antes del traslado sigue asociada al centro de costo donde se cargó.
- [x] Se puede consultar a qué centro de costo pertenecía un trabajador en una fecha pasada.
- [x] El estado de cumplimiento de un trabajador dado de baja deja de exigirse, sin borrar su historia.
- [x] El traslado y la baja quedan en la bitácora con autor, fecha y motivo.
- [x] El recorrido de aceptación cubre un traslado y comprueba que la reconstrucción histórica respeta la dotación de cada fecha.
