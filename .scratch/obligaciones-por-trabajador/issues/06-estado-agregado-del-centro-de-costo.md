# 06: Estado agregado del centro de costo

**What to build:** Que el plan de un centro de costo siga siendo la vista de trabajo diaria cuando las obligaciones son de personas. Para una obligación de titular trabajador, el centro muestra el peor estado presente y cuántas personas hay en cada uno —«Manejo de extintores: Vencido — 5 de 52»— y desde ahí se abre el desglose para saber cuáles cinco.

Hoy ese número no existe: el centro muestra el estado de la única evidencia que se cargó, como si cubriera a todos.

**Blocked by:** 03

**Type:** task

**Status:** resolved

- [x] Para una obligación de titular centro de costo, el caso de cumplimiento no cambia.
- [x] Para una obligación de titular trabajador, el caso del centro se calcula sobre los trabajadores asignados y validados a la fecha consultada que tienen esa obligación aplicable en su plan.
- [x] El estado agregado es el peor estado presente, con precedencia `Sin evidencia` > `Vencido` > `Pendiente de validación` > `Por vencer` > `Vigente`.
- [x] `Sin evidencia` y `Vencido` nunca se colapsan, y `Pendiente de validación` cuenta como no cumplido.
- [x] Se muestra cuántos trabajadores hay en cada estado.
- [x] Un trabajador con la obligación aplicable y sin ninguna evidencia aparece como `Sin evidencia` en el desglose.
- [x] Un centro sin ningún trabajador aplicable para esa obligación resulta `No aplica`.
- [x] Desde el estado agregado se abre el desglose por persona sin perder contexto.
- [x] El agregado se reconstruye a una fecha pasada usando la dotación que existía en esa fecha.
- [x] Ningún estado se teclea: todos se derivan de fechas, periodicidad, validación y aplicabilidad.
- [x] El recorrido de aceptación cubre el agregado con su recuento y la navegación al desglose.
