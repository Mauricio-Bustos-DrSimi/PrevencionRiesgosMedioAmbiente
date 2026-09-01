# 02: Corregir la fecha de un escaneo al validar

**What to build:** Que un Prevencionista abra una evidencia que quedó Pendiente de validación porque su documento no declaraba fechas, escriba la fecha que lee en el papel con su motivo, y el estado de cumplimiento se re-derive de ese dato. La evidencia original no se toca: el archivo y su hash siguen siendo los de la carga.

Hoy la pantalla de validación es un timbre: confirma o no confirma, y no tiene dónde escribir la fecha verdadera. Son 87 de los 245 documentos del piloto —los cuatro exámenes ocupacionales y las cinco licencias de conducir—, todos escaneos de clínica sin capa de texto, cargados con la fecha de emisión y la de vencimiento iguales al día de la siembra.

Este ticket no necesita que exista el trabajador: se demuestra sobre los datos que ADM04 ya tiene.

**Blocked by:** None (can start immediately)

**Type:** task

**Status:** resolved

- [x] Existe un registro de corrección de evidencia, append-only, con las fechas de emisión y vencimiento verdaderas, autor, motivo y momento.
- [x] La evidencia original y su archivo no se modifican: el hash sigue siendo el que se calculó al cargarla, y la verificación de integridad sigue dando coincidencia.
- [x] La vigencia se deriva de la corrección más reciente anterior a la fecha consultada.
- [x] La reconstrucción histórica sigue funcionando: consultar una fecha anterior a la corrección usa el dato que regía entonces.
- [x] La pantalla de validación acepta fechas corregidas de forma opcional.
- [x] Corrección y validación quedan registradas como dos actos separados, en una sola transacción, con dos eventos de bitácora distintos.
- [x] Validar sin corregir se comporta exactamente como hoy.
- [x] Se puede corregir una evidencia que ya fue validada.
- [x] Se rechaza una corrección con fecha de emisión futura o con vencimiento anterior o igual a la emisión, y el mensaje explica el motivo.
- [x] La pantalla muestra la fecha con que se cargó la evidencia y la fecha corregida, para que se vea qué se sabía en cada momento.
- [x] Corregir una fecha es distinguible de cargar una evidencia nueva, tanto en pantalla como en la bitácora.
- [x] El recorrido de aceptación cubre el tramo: escaneo sin fecha, corrección, validación y estado derivado del dato corregido.
