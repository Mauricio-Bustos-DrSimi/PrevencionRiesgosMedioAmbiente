# 09: Ciclo completo del trabajador en el recorrido de aceptación

**What to build:** La demostración reproducible de que una obligación de una persona recorre el ciclo entero —alta, carga a su nombre, corrección de fecha, validación, vencimiento, renovación y reconstrucción histórica— sin perder evidencia ni trazabilidad. Es la costura principal de la iniciativa y lo que habilita el paso siguiente: el piloto no puede completar un ciclo real de vencimiento y renovación mientras su material probatorio sea por persona y el sistema no lo sea.

Los tickets anteriores van agregando su tramo al recorrido; este lo cierra y comprueba que el ciclo completo queda verde de punta a punta.

**Blocked by:** 02, 06, 07, 08

**Type:** task

**Status:** resolved

- [x] El recorrido atraviesa alta de trabajador, confirmación de su plan, carga a su nombre, corrección de fecha, validación, paso del tiempo, renovación y reconstrucción histórica.
- [x] Comprueba el rechazo del intento de cargar sin indicar la persona cuando la obligación lo exige.
- [x] Comprueba que la evidencia original y su hash quedan intactos tras una corrección, y que la vigencia pasa a derivarse del dato corregido.
- [x] Comprueba el estado agregado del centro con su recuento y la navegación al desglose por persona.
- [x] Comprueba la reconstrucción histórica en el grano de la persona, con la dotación que correspondía a cada fecha.
- [x] La bitácora muestra el alta del trabajador, la corrección y la validación como actos distintos, en ambos canales.
- [x] El paso del tiempo usa el reloj simulado; no se manipulan fechas del sistema.
- [x] El recorrido exige PostgreSQL y se omite informando el motivo si la base configurada es otra.
- [x] La suite completa y la verificación de tipos quedan verdes.
- [x] La documentación del recorrido de aceptación y la del piloto describen la etapa nueva.
