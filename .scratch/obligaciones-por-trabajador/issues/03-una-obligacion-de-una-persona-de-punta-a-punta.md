# 03: Una obligación de una persona, de punta a punta

**What to build:** El camino completo de una obligación cuyo titular es un trabajador: dar de alta a una persona con su RUT y su cargo, asignarla a un centro de costo, confirmar que la obligación le aplica, cargar su evidencia a su nombre y ver **su** estado de cumplimiento derivado.

Es el tracer bullet de la iniciativa. Se hace delgado a propósito: una obligación, una persona, una pantalla. El estado agregado del centro, la sugerencia por cargo y las bandejas vienen después, apoyados en esto.

Incluye escribir la decisión: **ADR 0004** —la evidencia pertenece a un titular, y el centro de costo pasa de titular único a contexto— y el término **cargo** en `CONTEXT.md`.

**Blocked by:** None (can start immediately)

**Type:** task

**Status:** resolved

- [x] `CONTEXT.md` incorpora **cargo** con su definición y sus términos a evitar, y precisa que **trabajador** es un titular de obligación efectivo y que la evidencia se carga contra un titular.
- [x] ADR 0004 registra la decisión con su contexto, alternativas y consecuencias, explica por qué se prefiere una relación explícita opcional por sobre una polimórfica, y se relaciona con ADR 0001.
- [x] El trabajador se identifica por su RUT, único y normalizado a un formato canónico único; el nombre es un atributo y no la identidad.
- [x] Un RUT mal formado o con dígito verificador incorrecto se rechaza al registrarlo.
- [x] El mismo RUT escrito con puntos, sin puntos o con dígito verificador en minúscula identifica a la misma persona y no crea un duplicado.
- [x] El trabajador registra su cargo.
- [x] La pertenencia a un centro de costo se registra como una asignación **append-only** con fecha, autor y motivo; la vigente se deriva de la última.
- [x] Un trabajador nace no validado, un Prevencionista lo valida, y un trabajador no validado no produce cumplimiento.
- [x] El cambio de aplicabilidad admite como sujeto un trabajador además de un centro de costo, conservando autor, fecha, motivo y su carácter append-only, y sin cambiar el comportamiento actual para el centro.
- [x] Se puede confirmar individualmente que una obligación le aplica a un trabajador, y declarar que no le aplica con motivo.
- [x] La evidencia gana una relación **opcional** con el trabajador y conserva la que tiene con el centro de costo.
- [x] Si la versión de obligación declara titular trabajador, la evidencia exige indicar la persona y se rechaza sin ella, con un mensaje que explica por qué.
- [x] Si declara titular centro de costo, la evidencia rechaza que se indique una persona.
- [x] Se rechaza una evidencia a nombre de un trabajador que no estaba asignado a ese centro de costo en esa fecha.
- [x] Los titulares externo y empresa se rechazan explícitamente, en vez de aceptarse por omisión.
- [x] La carga y el estado por centro de costo siguen comportándose exactamente como hoy, y las evidencias ya cargadas siguen siendo válidas.
- [x] Existe una pantalla que muestra el estado de cumplimiento de un trabajador para cada obligación que le aplica, derivado y no tecleado.
- [x] El alta, la validación, la asignación y la carga a nombre de una persona quedan en la bitácora con su actor.
- [x] El recorrido de aceptación cubre el camino completo: alta, asignación, plan, carga a nombre de la persona y estado derivado.
- [x] La nomenclatura del esquema y del código es en español.
