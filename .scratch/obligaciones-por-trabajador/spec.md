# Atribuir las obligaciones a su titular real: el trabajador

Status: ready-for-agent

## Problem Statement

El Departamento de Prevención de Riesgos abre la pantalla de validación de una evidencia de la Bodega de Distribución (ADM04) y encuentra una **licencia de conducir que figura como obligación del centro de costo**. Una bodega no tiene licencia de conducir: la tienen las personas que conducen, cada una obtenida en una fecha propia y con un vencimiento propio.

El problema no es de presentación, y no se limita a la licencia. La siembra del piloto atribuye **todas** las obligaciones al titular `centro_costo`, y **14 de las 18** del plan de ADM04 tienen respaldo por persona: nueve capacitaciones (manejo de extintores con simulador, fortalecimiento de competencias psicosociales, orientación en prevención de riesgos laborales, prevención del consumo de alcohol y drogas, análisis del Decreto Supremo 44, liderazgo en seguridad y salud para supervisores, factores de riesgo TMERT, factores de riesgo MMC, gestión del riesgo de desastre), cuatro exámenes ocupacionales (altura física, conductor clase D, conductor de vehículo liviano, operadores de maquinaria) y la licencia de conducir.

Las 245 constancias de la carpeta de respaldo pertenecen las 245 a un trabajador identificado por su RUT: **ninguna es del centro de costo**. Las únicas obligaciones de ADM04 que sí son de la instalación son justamente las que no tienen ningún documento —matriz IPER, reglamento interno, comité paritario— más la vigilancia de sílice, que está en No aplica. El plan está invertido de punta a punta.

El catálogo declara los cuatro titulares de obligación desde el comienzo, pero `trabajador` nunca se usa, y las obligaciones sugeridas para un plan de aplicación filtran explícitamente por titular `centro_costo`, de modo que las obligaciones de persona entraron al plan del centro por una puerta que el dominio no había abierto.

De ahí se desprenden tres consecuencias que el departamento ve en pantalla:

1. **La carpeta de respaldo tiene 5 licencias de conducir de 5 personas distintas y el sistema cargó 1.** Lo mismo con el resto: 245 constancias de 129 trabajadores quedaron reducidas a 18 evidencias, una por obligación, la que caduca primero. No se puede saber quién está cubierto, cuántos faltan, ni renovarle la evidencia a alguien en particular.

2. **Las evidencias sin fecha legible quedaron con fechas de relleno.** Los exámenes ocupacionales y las licencias son escaneos sin capa de texto —87 de los 245 archivos— y se cargaron con la fecha de emisión y la de vencimiento iguales al día de la siembra, y con el campo emisor ocupado por una nota que avisa que la fecha está por confirmar.

3. **Validar no permite corregir esa fecha.** La validación de evidencia solo recibe al actor: escribe el acto de validación y nada más. La evidencia es append-only por decisión de ADR 0001 y rechaza cualquier modificación, así que la pantalla de validación no tiene dónde escribir la fecha verdadera que Prevención lee del documento. El procedimiento documentado del piloto promete que "la fecha la tiene que leer y confirmar Prevención", y hoy eso no se puede hacer.

El resultado es que el estado de cumplimiento de ADM04 afirma cosas que no son ciertas, y que el piloto no puede completar un ciclo real de vencimiento y renovación —la condición declarada para abrir el sistema a los Encargados— porque el 100 % de su material probatorio es por persona y el modelo no tiene personas.

## Solution

El **trabajador** pasa a ser un titular de obligación efectivo, no solo un término del vocabulario.

Cada evidencia se carga contra un titular explícito. Cuando la obligación es del centro de costo, nada cambia respecto de lo que hoy funciona. Cuando la obligación es del trabajador, la evidencia se carga a nombre de una persona identificada por su RUT, y el estado de cumplimiento se deriva **por persona**: cada trabajador tiene su propia licencia, con su propia fecha, en su propio estado.

El centro de costo sigue siendo el grano de la operación diaria, pero para una obligación de titular trabajador su estado deja de ser un valor inventado y pasa a ser un **agregado explícito** de los estados de las personas que lo componen: el centro muestra el peor estado presente y cuántas personas hay en cada uno. Un Prevencionista que ve "Manejo de extintores: Vencido — 5 de 52" puede abrir la lista y saber cuáles cinco.

Cada trabajador tiene un **plan de aplicación propio**, individual, que parte de una sugerencia según su cargo y se confirma persona por persona, con autor, fecha y motivo. Es el mismo mecanismo que ya rige para los centros de costo, aplicado al otro titular: la aplicabilidad no se hereda automáticamente del cargo.

Corregir lo que el sistema leyó mal de un documento se vuelve un acto trazable y distinto de la renovación. Un **registro de corrección** append-only, con autor, motivo y las fechas verdaderas, se asocia a la evidencia original sin tocarla: el archivo es el mismo, su hash sigue siendo el que se calculó al cargarlo, y la corrección manda al derivar la vigencia. Así se distingue "el escaneo no declaraba su fecha y Prevención la leyó" de "llegó un documento nuevo que reemplaza al anterior".

Las catorce obligaciones ya sembradas con titular equivocado se **retractan** en vez de borrarse: se cierran con una versión nueva que declara el motivo, la evidencia cargada queda consultable y la retractación misma queda en la historia. Es lo que exige el modelo append-only y, además, es el ensayo de cómo se corrige un error de datos maestros cuando esto esté en producción. Al terminar, ADM04 muestra solo las cuatro obligaciones que sí son suyas, que es el estado honesto: la bodega no tiene acreditado nada en el grano de la instalación.

Finalmente, la siembra del piloto deja de colapsar el respaldo: carga las 245 constancias atribuidas a la persona que las obtuvo, no una por obligación.

## User Stories

1. Como Prevencionista, quiero que una licencia de conducir esté asociada a la persona que la obtuvo, para que el sistema no afirme que la tiene la bodega.
2. Como Prevencionista, quiero registrar un trabajador con su RUT y su nombre, para identificar sin ambigüedad al titular de una obligación personal.
3. Como Prevencionista, quiero que el RUT sea la identidad canónica del trabajador, para reconocer a la misma persona entre distintas cargas de respaldo.
4. Como Prevencionista, quiero que el sistema rechace un RUT mal formado o con dígito verificador incorrecto, para no crear dos personas donde hay una.
5. Como Prevencionista, quiero asignar un trabajador a un centro de costo, para saber qué dotación responde por ese centro.
6. Como Prevencionista, quiero registrar el cargo de un trabajador, para partir de una sugerencia de obligaciones acorde a lo que esa persona hace.
7. Como Prevencionista, quiero confirmar individualmente el plan de aplicación de cada trabajador, para que la aplicabilidad no dependa automáticamente de su cargo.
8. Como Prevencionista, quiero declarar que una obligación no aplica a un trabajador determinado, para obtener No aplica con fundamento explícito y no un falso incumplimiento.
9. Como Prevencionista, quiero indicar autor, fecha y motivo en cada cambio del plan de un trabajador, para mantener trazabilidad comprobable.
10. Como Prevencionista, quiero cargar una evidencia a nombre de un trabajador, para acreditar una obligación que es suya y no de su centro.
11. Como Prevencionista, quiero que el sistema me exija indicar el trabajador cuando la obligación es de titular trabajador, para no volver a atribuirle al centro algo que es de una persona.
12. Como Prevencionista, quiero que el sistema me impida indicar un trabajador cuando la obligación es del centro de costo, para que el titular de cada evidencia sea inequívoco.
13. Como Prevencionista, quiero que el sistema rechace una evidencia a nombre de un trabajador que no pertenece al centro de costo indicado, para que la dotación y la evidencia no se contradigan.
14. Como Prevencionista, quiero ver el estado de cumplimiento de cada trabajador para cada obligación que le aplica, para saber a quién le falta qué.
15. Como Prevencionista, quiero ver en el plan del centro de costo un estado agregado para las obligaciones de titular trabajador, para conservar la vista por centro sin perder el grano de la persona.
16. Como Prevencionista, quiero que el estado agregado muestre el peor estado presente entre los trabajadores, para que una sola persona sin cobertura no quede escondida detrás del promedio.
17. Como Prevencionista, quiero ver cuántos trabajadores hay en cada estado dentro de una obligación agregada, para dimensionar el trabajo pendiente.
18. Como Prevencionista, quiero abrir el desglose por persona desde el estado agregado, para llegar al caso concreto sin perder contexto.
19. Como Prevencionista, quiero que un trabajador sin ninguna evidencia de una obligación que le aplica aparezca como Sin evidencia, para distinguir la omisión inicial del vencimiento.
20. Como Prevencionista, quiero corregir la fecha de emisión y de vencimiento de una evidencia cuyo documento no las declaraba, para que su vigencia se derive de lo que el documento realmente dice.
21. Como Prevencionista, quiero indicar el motivo de cada corrección de fechas, para que la historia explique por qué el dato cambió.
22. Como Prevencionista, quiero que la corrección de fechas no modifique la evidencia original ni su archivo, para preservar la historia append-only y el hash con que se cargó.
23. Como Prevencionista, quiero que la corrección de fechas y la validación queden registradas como actos distintos, para no confundir confirmar el documento con corregir lo que el sistema leyó de él.
24. Como Prevencionista, quiero poder corregir las fechas en el mismo envío en que valido, para resolver un escaneo sin fecha en una sola pasada.
25. Como Prevencionista, quiero que la vigencia se derive de la corrección más reciente cuando exista, para que el estado refleje el dato confirmado y no el de relleno.
26. Como Prevencionista, quiero que corregir una fecha sea distinto de cargar una evidencia nueva, para que la historia no diga "se renovó" cuando solo se leyó una fecha.
27. Como Fiscalizador, quiero ver la fecha con que se cargó una evidencia y la fecha corregida, para comprobar qué se sabía en cada momento.
28. Como Prevencionista, quiero que el sistema rechace una corrección cuyas fechas sean incoherentes, para no reemplazar un dato dudoso por uno imposible.
29. Como Departamento de Prevención de Riesgos, quiero retractar una obligación atribuida al titular equivocado sin borrarla, para corregir el error conservando lo que se registró.
30. Como Prevencionista, quiero que la retractación declare su motivo, para que quien la lea entienda que fue un error de atribución y no un cambio normativo.
31. Como Fiscalizador, quiero acceder a la evidencia de una obligación retractada, para comprobar qué se había cargado antes de la corrección.
32. Como Prevencionista, quiero que una obligación retractada deje de exigirse al centro de costo, para que su plan deje de mostrar un incumplimiento que no le corresponde.
33. Como Prevencionista, quiero que la siembra del piloto cargue todas las constancias del respaldo y no solo la que caduca primero, para trabajar con la cobertura real del centro.
34. Como Prevencionista, quiero que cada constancia sembrada quede atribuida al trabajador cuyo RUT la acompaña, para que la carpeta y el sistema digan lo mismo.
35. Como Prevencionista, quiero que la siembra cree los trabajadores que encuentra en el respaldo, para no darlos de alta a mano uno por uno.
36. Como Prevencionista, quiero que la siembra asigne el titular correcto a cada obligación según el catálogo, para que la licencia de conducir y los exámenes ocupacionales nazcan como obligaciones del trabajador.
37. Como Prevencionista, quiero que la siembra se niegue a atribuir constancias a personas cuando no tiene acceso a la carpeta original, para no inventar una dotación a partir de un resumen anónimo.
38. Como Departamento de Prevención de Riesgos, quiero que el resumen versionado del respaldo siga sin contener nombres ni RUT, para no incorporar datos personales al repositorio.
39. Como Prevencionista, quiero reconstruir el estado de cumplimiento de un trabajador en una fecha pasada, para evaluar su cobertura con el contexto que existía entonces.
40. Como Fiscalizador, quiero reconstruir el estado agregado de un centro de costo en una fecha pasada considerando la dotación de ese momento, para no juzgar el pasado con la dotación de hoy.
41. Como Prevencionista, quiero que la bandeja de vencimientos incluya las obligaciones de trabajador, para priorizar renovaciones de personas y no solo de instalaciones.
42. Como Prevencionista, quiero que la bandeja identifique a qué persona corresponde cada vencimiento, para saber a quién citar.
43. Como Prevencionista, quiero que la bandeja de pendientes de validación identifique al trabajador de cada evidencia, para procesar los escaneos sin fecha uno por uno.
44. Como Prevencionista, quiero filtrar la operación por trabajador además de por centro de costo, estado y obligación, para encontrar los casos que requieren acción.
45. Como Prevencionista, quiero que el alta, la asignación y el traslado de un trabajador queden en la bitácora, para que la dotación tenga la misma trazabilidad que la evidencia.
46. Como Prevencionista, quiero que cada corrección de fechas quede en la bitácora con su autor y su motivo, para que ninguna modificación de un dato quede sin explicación.
47. Como Prevencionista, quiero que la retractación de una obligación quede en la bitácora, para que la corrección del error sea tan comprobable como el error.
48. Como Departamento de Prevención de Riesgos, quiero que un trabajador creado por un Encargado quede en estado no validado, para que la dotación no crezca sin revisión de Prevención.
49. Como Prevencionista, quiero validar un trabajador no validado, para incorporarlo formalmente a la dotación del centro.
50. Como Departamento de Prevención de Riesgos, quiero que solo Prevención pueda trasladar o eliminar un trabajador, para que la dotación de un centro no cambie sin control.
51. Como Prevencionista, quiero que un trabajador no validado no produzca cumplimiento, para no sobreestimar la cobertura real del centro.
52. Como Departamento de Prevención de Riesgos, quiero que el recorrido de aceptación cubra el ciclo completo de una obligación de trabajador, para demostrar que el comportamiento temporal funciona también en el grano de la persona.
53. Como equipo de TI, quiero que el esquema y las interfaces sigan usando nomenclatura en español, para mantener coherencia con el vocabulario del proyecto.
54. Como Prevencionista, quiero seguir operando desde pantallas propias server-rendered, para hacer el trabajo diario sin depender del panel administrativo.

## Implementation Decisions

### Trabajador como titular de obligación

- Se crea una app `trabajadores` con el modelo `Trabajador`. Su identidad es el **RUT**, único y normalizado a un formato canónico único (sin puntos, con guion, dígito verificador en mayúscula), con validación de dígito verificador al registrarlo. El nombre es un atributo, no la identidad.
- `Trabajador` lleva un **cargo**, usado como fuente de la sugerencia inicial de obligaciones. El cargo es un dato del trabajador, no una entidad con plan propio: la aplicabilidad se confirma persona por persona, igual que hoy se confirma centro por centro.
- **`cargo` es vocabulario nuevo**: hay que incorporarlo a `CONTEXT.md` antes de implementar, junto con la precisión de que `trabajador` pasa de término declarado a titular efectivo.
- La pertenencia de un trabajador a un centro de costo es **histórica y append-only**, no un campo mutable: se modela como una asignación con fecha, autor y motivo, y la asignación vigente se deriva de la última. Sin esto, la reconstrucción histórica del estado agregado de un centro usaría la dotación de hoy para juzgar el pasado.
- `Trabajador` lleva un estado de validación (validado / no validado), coherente con el flujo declarado: el Encargado crea, Prevención valida. Un trabajador no validado no produce cumplimiento.
- Trasladar o eliminar un trabajador queda restringido a Prevención, y ambas operaciones son append-only: la eliminación es un cierre con motivo, no un borrado.

### El titular de una evidencia

- `Evidencia` conserva su relación con el centro de costo —el contexto operativo siempre se conoce, porque un trabajador pertenece a uno— y gana una relación **opcional** con `Trabajador`.
- La regla de integridad se valida al guardar, contra la versión de obligación asociada: si el titular declarado por la versión es `trabajador`, la evidencia **debe** indicar trabajador; si es `centro_costo`, **no debe** indicarlo. El trabajador indicado debe estar asignado al centro de costo de la evidencia en esa fecha.
- Se prefiere esta forma explícita por sobre una relación polimórfica: mantiene funcionando todas las consultas existentes por centro de costo, y convierte el agregado en un `group by` directo.
- Los titulares `externo` y `empresa` siguen sin implementarse; la validación debe rechazarlos explícitamente en vez de aceptarlos por omisión.
- Este cambio merece **ADR 0004**: la evidencia pertenece a un titular, y el centro de costo pasa de ser el titular único a ser el contexto.

### Corrección de fechas

- Se crea `CorreccionEvidencia`, append-only, asociada a una evidencia: fechas de emisión y vencimiento verdaderas, autor, motivo y momento. Una evidencia puede acumular varias; **manda la más reciente anterior a la fecha consultada**, de modo que la reconstrucción histórica siga funcionando.
- El archivo y su hash **no se tocan**: la corrección enmienda lo que el sistema leyó del documento, no el documento.
- La derivación de vigencia deja de leer las fechas directamente de la evidencia y pasa a leer las **fechas efectivas** en una fecha dada, que resuelven la corrección aplicable. Es el único punto que necesita cambiar en el cálculo de estados: la lógica de vigencia, periodicidad y umbral de "por vencer" queda igual.
- Una corrección se valida con las mismas reglas que la carga: emisión no futura, vencimiento posterior a la emisión.
- La pantalla de validación acepta fechas corregidas de forma opcional. Si vienen y difieren de las vigentes, se escribe la corrección y la validación como **dos actos separados** en una sola transacción, con dos eventos de bitácora distintos. Validar sin corregir sigue funcionando exactamente como hoy.
- La corrección es independiente de la validación: se puede corregir una evidencia ya validada.

### Estado agregado por centro de costo

- Para una obligación de titular `centro_costo`, el caso de cumplimiento no cambia.
- Para una obligación de titular `trabajador`, el caso del centro se calcula sobre los trabajadores **asignados y validados a la fecha consultada** que tienen esa obligación aplicable en su plan individual. El resultado lleva el estado agregado y el recuento por estado.
- La precedencia del agregado, de peor a mejor: `Sin evidencia` > `Vencido` > `Pendiente de validación` > `Por vencer` > `Vigente`. Un centro sin ningún trabajador aplicable para esa obligación resulta `No aplica`.
- La precedencia respeta la distinción del dominio: `Sin evidencia` y `Vencido` nunca se colapsan, y `Pendiente de validación` cuenta como no cumplido.
- Las bandejas operativas pasan a enumerar casos con su titular: un vencimiento de trabajador se muestra a nivel de persona, no del agregado, para que la bandeja siga siendo accionable.

### Sugerencia y plan de aplicación del trabajador

- La sugerencia de obligaciones para un centro de costo mantiene su filtro por titular `centro_costo`. La sugerencia para un trabajador es su espejo: obligaciones vigentes de titular `trabajador`, filtradas por el cargo de la persona.
- La versión de obligación gana un campo de cargos sugeridos, análogo al de tipos de centro, con la misma semántica: vacío significa todos.
- El cambio de aplicabilidad se generaliza para admitir como sujeto un centro de costo o un trabajador, conservando autor, fecha y motivo, y conservando su carácter append-only.

### Retractación de lo ya sembrado

- Se agrega un comando de gestión que cierra las catorce obligaciones de ADM04 con respaldo por persona —las nueve capacitaciones, los cuatro exámenes ocupacionales y la licencia de conducir— mediante una versión de obligación de tipo cierre, con autor y motivo explícito de error de atribución.
- El comando es idempotente, exige confirmación explícita como la siembra, y registra cada cierre en la bitácora con un canal propio que lo distinga de la operación normal.
- No borra evidencia ni cambios de aplicabilidad. La evidencia cargada queda consultable.
- Una obligación cerrada ya se excluye de la operación vigente; hay que **verificar durante la implementación** si además hace falta un cambio de aplicabilidad para que el plan del centro deje de exigirla, y cubrir el resultado con una prueba.

### Siembra del piloto

- La siembra deja de fijar el titular a `centro_costo` para todo: lo toma del catálogo, que pasa a declararlo obligación por obligación.
- La siembra deja de cargar una sola constancia por obligación: carga todas, cada una atribuida al trabajador cuyo RUT nombra su carpeta, dando de alta a los trabajadores que encuentre.
- **El resumen versionado del respaldo sigue siendo anónimo**, sin nombres ni RUT, y por lo tanto ya no basta para sembrar: la atribución exige leer la carpeta original. Sembrar con trabajadores sin la carpeta debe fallar con ese motivo, no degradar en silencio a la carga por centro.
- Las constancias sin fecha legible se siguen cargando pendientes de validación, ahora una por persona, para que Prevención las corrija con el mecanismo de corrección.
- La periodicidad y la norma de origen del catálogo siguen siendo **preliminares** y ajenas a esta spec: son una decisión del departamento.

## Testing Decisions

Una buena prueba en este repositorio comprueba **lo que el usuario ve a través de HTTP**: recorre las mismas vistas que usa el Departamento de Prevención de Riesgos, no llama a los servicios por dentro y no afirma nada sobre cómo está implementado el cálculo. En particular, ninguna prueba debe escribir un estado de cumplimiento: los estados se comprueban por lo que aparece en pantalla después de que las fechas, la periodicidad y la aplicabilidad los produzcan.

**Costura única: el recorrido de aceptación del MVP.** Es la costura más alta que existe y ya cubre el ciclo completo. Se extiende con la etapa del trabajador, intercalada entre la validación y el paso del tiempo:

- alta de un trabajador y confirmación de su plan individual;
- carga de evidencia a su nombre para una obligación de titular trabajador, y rechazo del intento de cargarla sin indicar persona;
- validación de un escaneo sin fecha **corrigiendo** las fechas, comprobando que la evidencia original y su hash quedan intactos y que la vigencia pasa a derivarse del dato corregido;
- estado agregado del centro con su recuento por estado, y navegación al desglose por persona;
- el paso del tiempo, la renovación y la reconstrucción histórica, que ya existen, aplicados ahora también a la obligación de la persona, con la dotación que correspondía a cada fecha;
- la bitácora, que debe mostrar el alta del trabajador, la corrección y la validación como actos distintos.

El recorrido exige PostgreSQL y **se omite** cuando la base configurada es otra; una ejecución omitida no sirve como demostración. Debe quedar verde antes de ampliar el piloto.

Solo se agregan pruebas por app donde el recorrido no alcance:

- la retractación de las catorce obligaciones mal atribuidas, junto a las pruebas de la siembra, verificando que la evidencia sigue consultable y que la operación es idempotente;
- la siembra con atribución por RUT y su negativa a sembrar sin la carpeta original;
- la normalización y validación del RUT, que es lógica pura y no necesita HTTP.

Prior art a seguir: el recorrido de aceptación existente para la costura principal; las pruebas HTTP de carga, renovación, bandeja de vencimientos y operación del piloto para el estilo de las pruebas por pantalla; las pruebas de trazabilidad para comprobar la bitácora en ambos canales; las pruebas de lectura de constancias para la lógica pura. El reloj simulado del recorrido de aceptación es el mecanismo para el paso del tiempo: no se manipulan fechas del sistema.

## Out of Scope

- **Equipos como titular de obligación.** Un extintor o una máquina con certificado propio es un quinto titular que el vocabulario no declara y del que la carpeta de respaldo no tiene un solo documento. Se aborda cuando exista material.
- **Externos y verificaciones por faena** (paso 6 de la secuencia) y **obligaciones de empresa, Ley REP y notificaciones por correo** (paso 7).
- **Rol Encargado y filtrado por centro de costo propio** (paso 4). Esta spec deja el modelo listo para que el Encargado cree trabajadores no validados, pero no crea el rol ni el alcance por centro.
- **Integración con RRHH.** La dotación se sigue manteniendo desde el respaldo y a mano. Los 129 RUT del piloto salen de la carpeta.
- **Confirmar la periodicidad y la norma de origen del catálogo de ADM04.** Es una decisión del departamento y es la que decide si una constancia aparece vigente o vencida; no es trabajo de código, pero condiciona lo que se verá al terminar esto.
- **Ampliar el piloto a 8-10 centros con respaldo real.** Se retomará una vez que la atribución por titular esté correcta, para no replicar el error a ocho centros más.
- **Rehacer la base del piloto.** Se decidió retractar en vez de resembrar; volver a evaluarlo después es una decisión abierta, no parte de esta spec.

## Further Notes

- **Los exámenes ocupacionales son datos de salud de una persona identificada.** Mientras la evidencia colgaba del centro de costo, la siembra evitaba deliberadamente que el nombre del archivo identificara a nadie. Al atribuirla a la persona, quién puede abrir ese archivo deja de ser una pregunta teórica. Esta spec no crea el rol Encargado, así que el riesgo no se materializa todavía, pero **debe resolverse antes del paso 4**: un Encargado no debería poder abrir el examen ocupacional de su subordinado. Conviene registrarlo como riesgo abierto en `CLAUDE.md`.
- Esta spec adelanta el paso 5 de la secuencia de construcción por sobre el paso 4. La razón es que el paso 4 está bloqueado por una condición declarada —que el piloto complete un ciclo real de vencimiento y renovación— que el modelo actual no puede satisfacer, porque todo el material probatorio del piloto es por persona.
- El vocabulario de `CONTEXT.md` ya define `trabajador`, `titular de obligación` y `evidencia` en términos compatibles con este cambio. Lo que falta agregar es `cargo`, y precisar que la evidencia se carga contra un titular.
- El respaldo real de ADM04 da la escala esperada: 129 trabajadores, 245 constancias, 6 cargos, y 87 escaneos sin fecha que ejercitarán el mecanismo de corrección desde el primer día.
