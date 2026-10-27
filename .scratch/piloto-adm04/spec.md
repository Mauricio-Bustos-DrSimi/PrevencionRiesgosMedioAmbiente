# Especificación de validación de negocio del piloto ADM04

Status: needs-info

## Objetivo

Convertir las decisiones confirmadas por Prevención para la Bodega de
Distribución ADM04 en una definición verificable del catálogo del piloto. La
especificación fija el universo en **18 obligaciones** y separa lo que ya fue
decidido de las fuentes, periodicidades y responsables que todavía deben ser
confirmados.

ADM04 es exclusivamente un entorno de prueba. Una obligación puede quedar
**Validada para demostración** con datos preliminares visibles, pero solo puede
quedar **Aprobada para operación** cuando cuenta con fuente y regla formalmente
confirmadas. Ninguna regla, evidencia ni decisión del piloto adquiere validez
operativa por haber sido usada en la demostración.

## Problema

El catálogo actual de ADM04 mezcla hechos obtenidos de las constancias con
normas y periodicidades preliminares. También representa como una sola evidencia
algunas obligaciones que en realidad exigen componentes distintos y carece de
los datos necesarios para gobernar responsables, aprobación administrativa y
decisiones de No aplica. Si esas reglas preliminares se interpretaran como
operativas, el sistema podría mostrar obligaciones vigentes o vencidas sin una
decisión formal de Prevención.

## Solución acordada

1. Mantener exactamente 18 obligaciones en el universo de revisión de ADM04.
2. Registrar obligaciones complementarias o programas materialmente distintos
   en una lista separada, sin ampliar el universo durante la validación.
3. Validar cada obligación por su titular, fuente, regla temporal,
   aplicabilidad, responsables y evidencia.
4. Distinguir el estado administrativo de la obligación del estado de
   cumplimiento derivado de sus evidencias.
5. Mantener ADM04 aislado de cualquier entorno operativo.
6. Preservar versiones, asignaciones, decisiones y transiciones como registros
   históricos append-only.

## Vocabulario y estados

### Estado administrativo de una versión de obligación

- **Borrador:** definición incompleta o todavía en revisión.
- **Validada para demostración:** puede utilizarse con datos de prueba y solo
  dentro del entorno de demostración. No genera alertas ni indicadores
  operativos y no admite evidencia real.
- **Aprobada para operación:** fuente y regla confirmadas formalmente. Este
  estado solo existe en el entorno operativo.
- **Cerrada:** versión que dejó de regir desde una fecha determinada.

El estado administrativo no reemplaza los estados de cumplimiento **Vigente**,
**Por vencer**, **Vencido**, **Pendiente de validación**, **Sin evidencia** y
**No aplica**, que continúan derivándose de vigencia, validación y
aplicabilidad.

### Jerarquía de fuentes

Ante contradicción prevalece, en este orden:

1. Norma legal vigente.
2. Resolución, protocolo o instrucción de la autoridad competente.
3. Matriz corporativa aprobada.
4. Procedimiento o política corporativa.
5. Criterio local documentado para ADM04.

Toda excepción local debe registrar fuente, responsable, justificación y
período de vigencia.

## Catálogo definitivo del universo de revisión

La tabla es definitiva respecto de las **18 filas** que se revisarán. Un valor
marcado **Pendiente** no se sustituye por la norma o periodicidad preliminar del
código actual. Los nombres que todavía requieren confirmación corporativa se
mantienen identificados como tales.

| N.º | Nombre oficial | Titular | Norma, matriz o documento de origen | Periodicidad | Aplicabilidad | Estado esperado | Responsable de validación | Evidencia requerida | Observaciones de negocio |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | **Pendiente de confirmar.** Grupo visual aprobado: “Capacitación en uso y manejo de extintores” | Trabajador | **Pendiente:** programa o matriz oficial de cada componente | **Pendiente para cada componente.** La vigencia global termina cuando vence primero cualquiera de los dos | Trabajador al que la regla oficial asigne ambas competencias, según función y riesgo efectivos | Validada para demostración. Vigente solo con ambos componentes validados; si alguno está pendiente, queda Pendiente de validación. **El estado global restante está pendiente de definición:** debe establecerse la precedencia entre Vencido y Sin evidencia cuando los componentes estén en estados diferentes | Área, titular y reemplazante pendientes | 1) Formación teórica online. 2) Práctica presencial con simulador. Cada evidencia debe identificar su componente | Son actividades distintas dentro de una obligación. Renovar un componente no elimina la vigencia del otro. No pueden representarse como documentos indistinguibles |
| 2 | **Pendiente:** nombre corporativo oficial del programa de riesgos psicosociales aplicable a ADM04 | Trabajador | **Pendiente:** programa corporativo, matriz y organismo responsable | **Pendiente:** evento inicial y renovación del programa oficial | Población objetivo definida por el programa corporativo | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Evidencia del programa oficial aplicable, con objetivo, temario, organismo y población identificables | Variantes ortográficas del mismo programa se agrupan. Un programa materialmente diferente queda en la lista adicional |
| 3 | Orientación en prevención de riesgos laborales — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** fuente legal y regla corporativa formal | Por evento: ingreso; cambio de cargo, proceso, centro o exposición; cambio de los riesgos informados. Renovación periódica solo si una regla corporativa la exige | Trabajador afectado por cualquiera de los eventos definidos | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia de orientación que identifique trabajador, contenido o riesgos informados y evento que la originó | Se descarta la anualidad preliminar como regla operativa |
| 4 | Capacitación y constancia de conocimiento de la política de prevención del consumo de alcohol y drogas — **nombre oficial pendiente** | Trabajador | **Pendiente:** política corporativa oficial | Al ingreso y cuando cambie sustancialmente la política. Repetición periódica solo si la política la exige | Toda la dotación únicamente si la política corporativa así lo establece | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia individual de capacitación y conocimiento de la política | Exámenes y controles quedan fuera de esta obligación y requieren revisión legal y de privacidad |
| 5 | Análisis del Decreto Supremo 44 — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** norma y matriz o programa corporativo que exija la capacitación | **Pendiente** | Jefaturas y personas con responsabilidad formal en gestión preventiva, según función efectiva | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia individual del programa oficial | Prevención debe definir la lista oficial de cargos o funciones equivalentes |
| 6 | Liderazgo en seguridad y salud — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** matriz o programa corporativo | **Pendiente** | Supervisores y jefaturas con trabajadores a cargo, según función efectiva | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia individual del programa oficial | La aplicación no debe decidir por coincidencia con el texto libre del cargo |
| 7 | Capacitación sobre factores de riesgo TMERT — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** evaluación de riesgo y fuente oficial del programa | **Pendiente** | Personas expuestas a tareas repetitivas o factores ergonómicos aplicables, según evaluación de riesgos | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia individual de la capacitación oficial | La evaluación del puesto o instalación es una obligación adicional. No se asigna por analogía con otra persona del mismo cargo |
| 8 | Capacitación sobre factores de riesgo por manejo manual de carga — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** evaluación de riesgo y fuente oficial del programa | **Pendiente** | Personas que efectivamente realizan manejo manual de carga, según evaluación de riesgos | Validada para demostración; cumplimiento derivado por trabajador | Área, titular y reemplazante pendientes | Constancia individual de la capacitación oficial | La evaluación del puesto o instalación es una obligación adicional. No se asigna por analogía con otra persona del mismo cargo |
| 9 | Plan de emergencia y gestión del riesgo de desastre vigente | Instalación | **Pendiente:** norma, matriz y documento corporativo aprobados | Anual para demostración; además ante cambios de infraestructura, rutas de evacuación, procesos, riesgos o responsables, y después de simulacros con hallazgos relevantes. Regla operativa pendiente de fuente oficial | ADM04 como instalación | Validada para demostración. Sin evidencia mientras no exista un plan que satisfaga la evidencia mínima | Prevención y contraparte de ADM04; personas titular y reemplazante pendientes | Plan aprobado, responsables, fecha, registro de simulacro y acciones correctivas | Las constancias individuales solo respaldan comunicación o capacitación; no acreditan por sí solas la existencia y vigencia del plan |
| 10 | Examen ocupacional para trabajo en altura física — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** protocolo, examen o prestador autorizado que defina la regla | La vigencia indicada por el examen, protocolo o prestador autorizado | Quien efectivamente trabaja en altura | Validada para demostración; cumplimiento derivado por trabajador y fechas confirmadas | Salud Ocupacional como área propuesta; titular y reemplazante pendientes | Examen ocupacional individual con resultado habilitante y vigencia legible o corregida por Prevención | Aplicabilidad por tarea y riesgo vigentes, aunque el cargo tenga otro nombre |
| 11 | Examen ocupacional para conductor clase D — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** protocolo, examen o prestador autorizado que defina la regla | La vigencia indicada por el examen, protocolo o prestador autorizado | Quien conduce equipos que requieren esa licencia o aptitud | Validada para demostración; cumplimiento derivado por trabajador y fechas confirmadas | Salud Ocupacional como área propuesta; titular y reemplazante pendientes | Examen ocupacional individual con resultado habilitante y vigencia legible o corregida | Es independiente de la licencia de conducir |
| 12 | Examen ocupacional para operadores de maquinaria — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** protocolo, examen o prestador autorizado que defina la regla | La vigencia indicada por el examen, protocolo o prestador autorizado | Quien opera la maquinaria correspondiente | Validada para demostración; cumplimiento derivado por trabajador y fechas confirmadas | Salud Ocupacional como área propuesta; titular y reemplazante pendientes | Examen ocupacional individual correspondiente a la maquinaria, con resultado y vigencia | Deben identificarse las maquinarias y aptitudes comprendidas |
| 13 | Examen ocupacional para conductor de vehículo liviano — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** protocolo, examen o prestador autorizado que defina la regla | La vigencia indicada por el examen, protocolo o prestador autorizado | Quien conduce vehículos livianos por función laboral | Validada para demostración; cumplimiento derivado por trabajador y fechas confirmadas | Salud Ocupacional como área propuesta; titular y reemplazante pendientes | Examen ocupacional individual con resultado habilitante y vigencia | Aplicabilidad por tarea efectiva, no solo por nombre de cargo |
| 14 | Licencia de conducir vigente — **nombre oficial pendiente de confirmación** | Trabajador | **Pendiente:** fuente aplicable y regla corporativa de conducción | Hasta la fecha impresa en la licencia; revisar ante vencimiento, suspensión, cambio de clase o cambio de función | Quien conduce por función efectiva; la clase debe corresponder al vehículo o maquinaria utilizada | Validada para demostración; cumplimiento derivado por trabajador y fecha impresa | Área, titular y reemplazante pendientes | Licencia individual con clase y vencimiento legibles o corregidos por Prevención | Es independiente del examen ocupacional. Se descarta una periodicidad anual artificial |
| 15 | Matriz IPER vigente — **nombre oficial pendiente de confirmación** | Instalación | **Pendiente:** fuente normativa y matriz corporativa aprobada | Anual para demostración; también ante cambios de procesos, equipos, sustancias, infraestructura, riesgos, dotación o funciones, y después de accidente grave o hallazgo relevante. Regla operativa pendiente | ADM04 como instalación | Validada para demostración. Sin evidencia mientras no exista una versión acreditada | Prevención y contraparte de ADM04; titular y reemplazante pendientes | Versión formal de la matriz, fecha, responsables y antecedentes de aprobación | Una versión nueva cierra la anterior y conserva la trazabilidad |
| 16 | Reglamento Interno de Higiene y Seguridad vigente | Instalación | **Pendiente:** norma vigente y política corporativa aplicable | Revisión programada según norma y política; además ante cambios normativos, de procesos, riesgos, razón social, antecedentes del documento o emisión formal de una nueva versión | ADM04 como instalación | Validada para demostración. Sin evidencia mientras no exista una versión vigente acreditada | Área, titular y reemplazante pendientes | Reglamento vigente formalmente emitido, con versión y período de vigencia | La constancia de entrega al trabajador queda en la lista adicional y no forma parte de esta fila |
| 17 | Comité Paritario de Higiene y Seguridad constituido — **nombre oficial pendiente de confirmación** | Instalación | **Pendiente:** norma legal vigente y documentos corporativos aplicables | Hasta terminar el período oficial del comité, todavía pendiente de confirmación | ADM04 solo cuando se cumpla el umbral legal confirmado por Prevención | Validada para demostración. Sin evidencia si aplica y no existe constitución acreditada; No aplica solo mediante decisión documentada | Área, titular y reemplazante pendientes | Documentos de constitución, período, integrantes y cambios o reemplazos exigidos por la fuente oficial | Prevención debe confirmar umbral, duración, documentos, vacancias y reemplazos. Una baja de dotación no cambia automáticamente a No aplica |
| 18 | Evaluación de exposición ocupacional a sílice | Instalación | **Pendiente:** protocolo, matriz y fuente oficial aplicables | Anual para demostración y ante cambios de proceso, riesgo, equipo, dotación o instalación. Regla operativa pendiente | ADM04 como instalación cuando exista una condición que requiera evaluar el riesgo | Validada para demostración. Puede quedar No aplica únicamente con decisión documentada y revisable; si confirma exposición, activa una obligación adicional del trabajador | Higiene Ocupacional o Prevención como área propuesta; titular y reemplazante pendientes | Evaluación de presencia o ausencia del riesgo. Si se decide No aplica: motivo, condición evaluada, evidencia, prevencionista y fecha | La vigilancia individual de salud por exposición confirmada queda en la lista adicional |

## Decisiones confirmadas

### Gobierno y aprobación

- El responsable titular aprueba formalmente la regla; Sysadmin registra la
  aprobación y administra el sistema; el usuario ejecutor queda automáticamente
  en la bitácora.
- El permiso técnico no sustituye la autoridad de negocio. Si una misma persona
  actúa como Sysadmin y responsable titular, ambos roles quedan registrados.
- La aprobación exige fecha, fuente y motivo.
- Solo Sysadmin cambia el estado administrativo y accede a la acción **Asignar
  responsables**, pero el servidor también debe verificar el permiso ante una
  petición directa.
- Cada obligación registra área responsable, responsable titular,
  reemplazante, fecha de vigencia de la asignación, motivo y usuario Sysadmin
  ejecutor.
- Titular y reemplazante se seleccionan entre usuarios activos. La asignación
  no agrega grupos ni concede permisos.
- El reemplazante no asume automáticamente por vacaciones. Cuando actúa, la
  bitácora registra que intervino como reemplazo.
- Las asignaciones son append-only: cada cambio cierra la asignación anterior y
  preserva a los responsables históricos aunque sus cuentas se desactiven.

### Catálogo de áreas responsables

El catálogo inicial controlado por Sysadmin contiene las siete áreas aprobadas:

- Prevención.
- Salud Ocupacional.
- Higiene Ocupacional.
- Recursos Humanos.
- Relaciones Laborales.
- Legal.
- Jefatura del centro de costo.

Solo permanecen pendientes la asignación del área correspondiente a cada
obligación y la selección de los usuarios activos que actuarán como responsable
titular y reemplazante.

### Acta de aprobación

La aprobación para operación exige un acta o documento con:

- identificador único;
- fecha;
- versión aprobada de la obligación;
- fuente revisada;
- responsable titular;
- participantes;
- decisión y observaciones;
- archivo o enlace al documento original.

La aplicación conserva la referencia al acta. Una validación de demostración
no se convierte en aprobación operativa.

### Versionado de reglas

- La secuencia administrativa es Borrador, Validada para demostración,
  Aprobada para operación y Cerrada.
- Ninguna transición anterior se edita, elimina o revierte.
- Una corrección normativa crea una versión nueva en Borrador.
- La versión anterior permanece vigente hasta la fecha efectiva del cambio y
  luego se cierra.
- La aplicabilidad y la regla temporal se evalúan nuevamente para la versión
  nueva.
- Las evidencias permanecen asociadas a la versión que las exigió.
- El cumplimiento se recalcula desde la fecha efectiva de la nueva versión,
  sin declarar incumplimientos retroactivos.
- Los casos afectados se muestran como pendientes de adecuación.

### No aplica

Una decisión de No aplica debe registrar:

- motivo concreto;
- riesgo, proceso o condición evaluada;
- evidencia justificativa;
- Prevencionista responsable;
- fecha de decisión;
- próxima revisión anual;
- reactivación ante cambios de proceso, riesgo, equipo, dotación o instalación;
- historial de decisiones anteriores.

Mientras el sistema no represente todos estos datos, No aplica solo puede
utilizarse en la demostración.

### Evidencia con fecha ausente o ilegible

1. Si la fecha es visible para una persona, Prevención registra una corrección
   con autor y motivo y después valida la evidencia.
2. Si la fecha también es ausente o ilegible para una persona, la evidencia
   permanece Pendiente de validación y se solicita reemplazo. No se inventa una
   fecha.
3. Si el documento no tiene fecha porque la obligación es por evento, solo se
   acepta cuando la regla oficial define el dato que determina su vigencia.

### Cargo y segunda función

- El registro vigente de Recursos Humanos es la fuente principal del cargo.
- Para cada uno de los tres casos detectados se confirma cargo oficial, centro
  de costo, fecha efectiva, segunda función temporal y tareas o riesgos reales.
- La cantidad de constancias no decide el cargo.
- Una segunda función actúa como condición de aplicabilidad y no sustituye el
  cargo oficial.
- El acta compartida registra solo el número de caso, cargo oficial, fecha
  efectiva, segunda función, fuente consultada y responsable que confirmó. No
  incluye nombres ni RUT.

### Aislamiento de ADM04

- Base de datos, directorio de medios, clave y variables separados.
- Etiqueta visual **DEMOSTRACIÓN**.
- `DJANGO_ENTORNO=demo` funciona como señal, pero no es la única barrera.
- Está prohibido copiar evidencias o registros desde demostración a producción.
- Una regla aprobada se recrea o importa como un registro nuevo en producción y
  conserva la referencia al acta de aprobación.
- Una versión Validada para demostración nunca se transforma físicamente en un
  registro productivo.

## Supuestos descartados

- Las normas incluidas actualmente en el catálogo de demostración no se
  consideran confirmadas por ser plausibles.
- Las periodicidades anual o bienal configuradas actualmente no se consideran
  reglas operativas por existir en el código.
- Una constancia individual de emergencia no acredita por sí sola el plan de
  la instalación.
- La vigilancia individual de salud por exposición a sílice no reemplaza la
  evaluación de exposición de la instalación.
- La cantidad de constancias no determina el cargo de una persona.
- Compartir cargo con otra persona no determina automáticamente aplicabilidad.
- Las variantes ortográficas no crean obligaciones distintas.
- Dos programas materialmente diferentes no se fusionan por tener nombres
  similares.
- Formación online y práctica con simulador no son evidencias equivalentes.
- La licencia de conducir y el examen ocupacional para conducir no son la misma
  obligación.
- No aplica no es permanente ni se activa automáticamente por una variación de
  dotación.
- Una fecha ausente o ilegible no se inventa.
- La vigencia de licencias y exámenes no se fuerza a un ciclo anual.
- Una regla de ADM04 no pasa a producción por quedar Validada para demostración.
- Sysadmin no adquiere autoridad de negocio por tener permisos técnicos.
- La asignación de responsables no concede permisos ni membresía en grupos.
- Una transición o asignación histórica no se edita ni se borra.

## Datos aún pendientes

La especificación permanece en `needs-info` hasta resolver, para cada fila, los
datos exigidos por el criterio de cierre:

- nombre corporativo oficial donde la tabla lo indica;
- fuente normativa, matriz, protocolo, política o programa con su versión;
- periodicidad concreta o evento de renovación;
- criterios completos de aplicabilidad;
- área responsable definitiva;
- usuario responsable titular y reemplazante;
- acta y motivo de aprobación;
- fecha efectiva de la regla.

Además permanecen pendientes:

- periodicidad concreta de los dos componentes de extintores;
- estado global de extintores cuando sus componentes estén en estados
  diferentes, incluida la precedencia entre Vencido y Sin evidencia;
- identidad del programa psicosocial oficial aplicable a ADM04 y comparación de
  las seis variantes por objetivo, temario, organismo y población;
- lista oficial de cargos o funciones para Análisis del DS 44 y Liderazgo en
  seguridad y salud;
- umbral, duración, documentación, vacancias y reemplazos del Comité Paritario;
- confirmación mediante Recursos Humanos de los tres casos con segunda función;
- asignación de una de las siete áreas aprobadas a cada obligación y usuarios
  activos que actuarán como responsable titular y reemplazante;
- definición de qué entornos y procesos constituyen la barrera técnica adicional
  a `DJANGO_ENTORNO=demo`.

## Cambios que requieren código

### Permisos confirmados para el MVP

Estas reglas fueron confirmadas por el responsable del proyecto y reemplazan
las preguntas pendientes del ticket 05. No requieren acta, Excel ni entrevista
adicional:

- **Administrador:** corresponde técnicamente al Sysadmin existente. Tiene
  alcance global y acceso a todas las funciones y datos, incluidas gestión de
  usuarios, asignaciones, importaciones, archivos e integridad.
- **Prevencionista:** tiene alcance global sin asignación individual. Puede
  crear, modificar, validar, corregir, importar, descargar, verificar
  integridad y gestionar planes, obligaciones, trabajadores y evidencias.
- **Encargado:** consulta portada, indicadores, operación, vencimientos,
  centros, trabajadores, obligaciones, planes y estados exclusivamente para
  centros con asignación vigente. No modifica planes, obligaciones,
  trabajadores ni evidencias; no valida, corrige, traslada, da de baja,
  importa, administra, descarga archivos ni gestiona asignaciones.
- El alcance de Encargado se verifica siempre en el servidor y una petición
  directa a otro centro se rechaza.
- Los exámenes ocupacionales quedan restringidos a Administrador y
  Prevencionista. Se conserva el enmascaramiento de RUT y la protección de
  datos personales.
- **Lector, externos y franquicias** quedan fuera de esta implementación.
- Estas decisiones no cambian periodicidades, normas ni el universo de las 18
  obligaciones de ADM04.

1. **Componentes de evidencia.** Representar por separado la formación online
   y la práctica con simulador, y derivar el estado global y la primera fecha de
   vencimiento sin perder el componente todavía vigente.
2. **Estado administrativo versionado.** Incorporar Borrador, Validada para
   demostración, Aprobada para operación y Cerrada con transiciones append-only,
   fecha efectiva, autor, motivo y restricciones por entorno.
3. **Asignación histórica de responsables.** Incorporar área, titular,
   reemplazante, vigencia, motivo, actor Sysadmin y actuación como reemplazo.
4. **Catálogo controlado de áreas.** Permitir administración por Sysadmin y
   conservar áreas desactivadas en el historial.
5. **Aprobación y acta.** Exigir los campos de cierre, vincular la versión con el
   acta y separar responsable de negocio de usuario ejecutor.
6. **No aplica revisable.** Admitir evidencia justificativa, próxima revisión,
   vencimiento de la decisión, reactivación por cambios e historial.
7. **Reglas por evento y fecha externa.** Representar eventos de aplicabilidad y
   vigencias dictadas por licencia, examen, protocolo o prestador sin imponer
   anualidad.
8. **Versionado con fecha efectiva.** Mantener simultáneamente la versión
   anterior y la nueva hasta su fecha efectiva, preservar evidencia por versión
   y mostrar casos pendientes de adecuación sin retroactividad.
9. **Aislamiento reforzado.** Impedir en el servidor evidencia real e indicadores
   operativos para registros de demostración y evitar promoción física de un
   registro demo a producción.
10. **Permisos.** Mostrar Asignar responsables solo a Sysadmin y validar el
    permiso en el servidor ante peticiones directas.
11. **Aviso de demostración.** Mostrar la etiqueta DEMOSTRACIÓN cuando el
    entorno corresponda, sin usarla como única barrera.

## Cambios que solo requieren configuración o datos

Estos cambios no requieren código cuando el modelo final ya pueda representar
la decisión:

- completar los nombres corporativos oficiales;
- cargar las fuentes y versiones documentales confirmadas;
- cargar periodicidades o eventos confirmados;
- cambiar el titular de la fila de emergencia a instalación;
- sustituir la fila de entrega del reglamento por la versión vigente del
  reglamento de la instalación;
- sustituir vigilancia de sílice por evaluación de exposición de la instalación;
- registrar aplicabilidad individual según función y riesgo;
- registrar los cargos oficiales y segundas funciones confirmadas por Recursos
  Humanos;
- asignar área, responsable titular y reemplazante;
- registrar las actas y fechas efectivas;
- clasificar programas psicosociales materialmente diferentes en la lista
  adicional;
- configurar las variables, base y directorio de medios exclusivos de demo.

La carga de cualquiera de estos datos queda bloqueada en esta especificación:
no se ejecuta siembra ni se modifica una base de datos.

## Obligaciones adicionales separadas

Las siguientes decisiones no aumentan las 18 filas del piloto:

- constancia de entrega del Reglamento Interno al trabajador;
- vigilancia individual de salud cuando la evaluación confirme exposición a
  sílice;
- capacitación individual relacionada con el plan de emergencia;
- evaluación del puesto o instalación asociada a TMERT;
- evaluación del puesto o instalación asociada a manejo manual de carga;
- programas psicosociales materialmente diferentes del programa oficial de
  ADM04.

Los dos componentes de extintores pertenecen a la fila 1 y no son obligaciones
adicionales.

## Elementos fuera del piloto

- Uso operativo o productivo de las reglas preliminares de ADM04.
- Copia de evidencias, trabajadores, asignaciones o registros del piloto a
  producción.
- Promoción física de una obligación Validada para demostración.
- Ampliación del universo por sobre las 18 obligaciones durante esta revisión.
- Incorporación automática de las obligaciones adicionales al catálogo.
- Integración automática con Recursos Humanos.
- Administración de vacaciones o ausencias del responsable titular.
- Otorgamiento automático de permisos por una asignación de responsabilidad.
- Exámenes o controles asociados a alcohol y drogas antes de una revisión legal
  y de privacidad.
- Titulares externo o empresa y obligaciones ambientales ajenas a estas 18
  filas.
- Uso de evidencia real en el entorno de demostración.

## Historias de usuario

1. Como Prevencionista, quiero revisar exactamente 18 obligaciones, para cerrar
   el piloto sin cambiar el universo durante la sesión.
2. Como Prevencionista, quiero distinguir una regla preliminar de una aprobada,
   para que la demostración no produzca conclusiones operativas.
3. Como responsable titular, quiero aprobar formalmente una versión con su
   fuente y acta, para asumir autoridad de negocio sobre la regla correcta.
4. Como Sysadmin, quiero registrar la aprobación sin reemplazar al responsable
   titular, para separar autoridad de negocio y permiso técnico.
5. Como auditor, quiero reconstruir responsables, versiones y transiciones por
   fecha, para saber quién respondía por cada regla.
6. Como Prevencionista, quiero que extintores exija sus dos componentes, para
   que una actividad no oculte la ausencia de la otra.
7. Como Prevencionista, quiero separar programas psicosociales materialmente
   distintos, para no atribuirles una periodicidad común sin respaldo.
8. Como Prevencionista, quiero decidir aplicabilidad por función y riesgo
   efectivos, para evitar inferencias desde el nombre del cargo.
9. Como Prevencionista, quiero justificar y revisar No aplica, para reactivar la
   evaluación cuando cambien las condiciones.
10. Como Prevencionista, quiero dejar pendiente una evidencia sin fecha legible,
    para no inventar datos.
11. Como responsable del entorno operativo, quiero que los registros de ADM04
    permanezcan aislados, para impedir que datos de prueba generen alertas o
    indicadores reales.

## Decisiones de prueba

La costura principal será un recorrido HTTP que demuestre el comportamiento
externo del piloto sin depender de detalles internos. Cuando se implemente, debe
cubrir al menos:

- una obligación de demostración no aparece en un entorno operativo;
- una regla demo no acepta evidencia real ni alimenta indicadores operativos;
- la aprobación registra responsable titular, Sysadmin ejecutor, fuente, fecha,
  motivo y acta;
- una petición directa sin permiso no puede asignar responsables;
- cambiar responsables cierra la asignación anterior y preserva el historial;
- la baja de una cuenta o área no elimina sus asignaciones históricas;
- extintores no queda Vigente con un solo componente y conserva el componente
  vigente cuando se renueva el otro;
- No aplica requiere todos sus antecedentes y vuelve a revisión en la fecha o
  evento configurados;
- una versión nueva se aplica desde su fecha efectiva sin alterar el pasado;
- una evidencia sin fecha legible permanece pendiente;
- el universo de ADM04 sigue teniendo exactamente 18 obligaciones.

Las pruebas deben usar datos ficticios, base y medios aislados. No deben ejecutar
la siembra real de ADM04 ni acceder a documentos reales.

## Criterio de cierre de una obligación

Una fila solo puede quedar **Aprobada para operación** cuando tiene:

- nombre oficial;
- titular;
- fuente identificada y versionada;
- periodicidad o evento de renovación;
- aplicabilidad;
- tratamiento de No aplica;
- área responsable;
- responsable titular y reemplazante;
- estado administrativo;
- fecha efectiva, motivo y acta de aprobación;
- pendientes y obligaciones adicionales registrados por separado.

Una fila incompleta puede quedar **Validada para demostración** si todos los
datos preliminares están etiquetados de forma visible y permanece aislada de la
operación.
