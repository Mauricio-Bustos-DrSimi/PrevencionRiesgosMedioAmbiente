# Mapa: Atribuir las obligaciones a su titular real

Especificación: [spec.md](./spec.md)

## Tickets

| # | Ticket | Bloqueado por | Estado |
| --- | --- | --- | --- |
| 01 | [Retractar las obligaciones con respaldo por persona](./issues/01-retractar-obligaciones-con-respaldo-por-persona.md) | — | resolved |
| 02 | [Corregir la fecha de un escaneo al validar](./issues/02-corregir-la-fecha-de-un-escaneo-al-validar.md) | — | resolved |
| 03 | [Una obligación de una persona, de punta a punta](./issues/03-una-obligacion-de-una-persona-de-punta-a-punta.md) | — | resolved |
| 04 | [Trasladar y dar de baja a un trabajador](./issues/04-trasladar-y-dar-de-baja-a-un-trabajador.md) | 03 | resolved |
| 05 | [Sugerir el plan del trabajador según su cargo](./issues/05-sugerir-el-plan-del-trabajador-segun-su-cargo.md) | 03 | resolved |
| 06 | [Estado agregado del centro de costo](./issues/06-estado-agregado-del-centro-de-costo.md) | 03 | resolved |
| 07 | [Bandejas y filtros en el grano de la persona](./issues/07-bandejas-y-filtros-en-el-grano-de-la-persona.md) | 06 | resolved |
| 08 | [Sembrar ADM04 con la atribución del respaldo](./issues/08-sembrar-adm04-con-la-atribucion-del-respaldo.md) | 02, 03, 05 | resolved |
| 09 | [Ciclo completo del trabajador en el recorrido](./issues/09-ciclo-completo-del-trabajador-en-el-recorrido.md) | 02, 06, 07, 08 | resolved |

## Frontera

`01`, `02` y `03` no dependen de nada y pueden avanzar en paralelo:

- **01** es corto y hace que la pantalla deje de afirmar que una bodega tiene licencia de conducir.
- **02** desbloquea `/validar/` sobre los 87 escaneos que ADM04 ya tiene cargados, sin necesitar trabajadores.
- **03** es el tracer bullet: el camino completo de una obligación de una persona.

## Por qué este corte

Cada ticket es un corte vertical: atraviesa modelo, servicio, pantalla y prueba, y se
puede demostrar solo. `03` concentra el modelo del trabajador, su asignación
histórica, el plan individual y la carga con titular porque ninguna de esas partes
se demuestra por separado: son capas del mismo camino.

Ni la evidencia ni el cambio de aplicabilidad necesitan un refactor ancho. Ambos
ganan una referencia **opcional** al trabajador —expand puro—, así que no hay que
migrar filas ni cambiar las consultas por centro de costo que ya funcionan.

## Costura

Una sola: el recorrido de aceptación del MVP. Cada ticket agrega su tramo y `09`
cierra el ciclo. Solo tres tickets llevan además pruebas propias por app, donde el
recorrido no alcanza: la retractación (`01`), la validación del RUT (`03`) y la
siembra con atribución (`08`).

## Resultados

Los nueve tickets están implementados y resueltos. La suite completa queda
verde contra PostgreSQL (122 pruebas, incluido el recorrido de aceptación) y la
verificación de tipos también.

- **01.** `manage.py retractar_obligaciones_por_trabajador` cierra las catorce
  obligaciones mal atribuidas con motivo de error de atribución, en el canal de
  bitácora «Retractación del piloto». **Cerrar basta**: el plan se arma con el
  catálogo vigente y las consultas saltan lo cerrado, así que no hace falta un
  cambio de aplicabilidad —y agregarlo diría algo falso, que el centro decidió
  que no le aplica—. Cubierto por `test_cerrar_basta_y_no_agrega_cambios_de_aplicabilidad`.
- **02.** `CorreccionEvidencia`, append-only. La derivación de vigencia pasa a
  leer *fechas efectivas* en una fecha dada; la lógica de periodicidad y umbral
  no cambió. `/validar/` acepta fechas corregidas y escribe dos actos separados
  en una transacción; `/corregir/` sirve para lo ya validado.
- **03.** App `trabajadores` con RUT canónico, asignación histórica, validación
  y plan individual. `Evidencia` y `CambioAplicabilidad` ganan una referencia
  opcional al trabajador —expand puro, sin migrar filas—. ADR 0004 y el término
  **cargo** en `CONTEXT.md`.
- **04.** Traslado y baja append-only, restringidos a Prevención. La
  reconstrucción histórica usa la dotación de cada fecha.
- **05.** `cargos_sugeridos` en la versión de obligación, espejo de
  `tipos_centro`. Los seis cargos del respaldo de ADM04 salen de los grupos del
  resumen, así que la sugerencia es la que la carpeta acredita.
- **06.** Estado agregado con recuento y desglose por persona, con la
  precedencia `Sin evidencia` > `Vencido` > `Pendiente de validación` >
  `Por vencer` > `Vigente`.
- **07.** Las bandejas enumeran por persona y filtran por trabajador.
- **08.** La siembra carga las 245 constancias atribuidas por RUT y da de alta a
  las 129 personas. `--carpeta` pasó a ser obligatoria: sin ella falla con ese
  motivo. Verificado contra la carpeta real: 245 constancias reconocidas, 129
  personas, 0 sin RUT legible, 87 sin fecha, seis cargos, 1,1 s de lectura.
- **09.** El recorrido de aceptación atraviesa alta, plan, carga a nombre de la
  persona, rechazo sin persona, corrección, validación, agregado, desglose,
  paso del tiempo, renovación, reconstrucción histórica, traslado, baja y
  bitácora. Sigue exigiendo PostgreSQL y omitiéndose en otro motor.

### Lo que corrigió la revisión de código

- **La bandeja se degradaba con la dotación.** Resolver cada caso persona por
  persona costaba una consulta por persona y por obligación: medido a la escala
  real —129 trabajadores por 14 obligaciones— eran **más de 9.000 consultas y
  8,5 s** para pintar la bandeja. Ahora la dotación, los planes y las evidencias
  se leen en bloque: **5 consultas y 0,3 s**. `evidencias/tests/test_escala_bandejas.py`
  comprueba que el número de consultas **no crece** con la dotación.
- **Los titulares `externo` y `empresa` se rechazaban tarde.** La comprobación
  vivía en el modelo, pero la carga fallaba antes con un «No aplica» que no
  explicaba nada. La regla del titular se hace valer ahora en un solo lugar
  —`exigir_titular_coherente`— que usan tanto la carga como el guardado.
- **Un trabajador no validado producía cumplimiento** en su propia pantalla: su
  evidencia se leía Vigente. Ahora cuenta como no cumplida mientras Prevención
  no lo incorpore.
- **Faltaba el filtro por centro de costo** en las dos bandejas.
- **Un centro sin trabajadores aplicables devolvía «Sin configurar»** en vez de
  No aplica.
- **El plan de un trabajador ofrecía obligaciones del centro de costo**, que
  ninguna evidencia habría podido acreditar.
- Faltaban las pruebas de los seis cargos y de que cambiar el cargo no mueve un
  plan ya confirmado.

### Decisiones tomadas al implementar

- **El traslado queda en la bitácora del centro de destino**, no en la del
  origen: el recorrido de trazabilidad es por centro y obligación, y el acto
  registra dónde queda la persona. El origen conserva la evidencia que se
  cargó allí y su historia.
- **La retractación no toca las obligaciones que ya nacen con titular
  trabajador**, así que una base sembrada con el comando nuevo no necesita
  corrección y ejecutar la retractación sobre ella no hace nada.
- **Una constancia sin RUT válido detiene la siembra** en vez de omitirse: el
  respaldo real no tiene ninguna, y perder evidencia en silencio sería peor que
  fallar.
