# 07: Bandejas y filtros en el grano de la persona

**What to build:** Que las bandejas operativas sigan siendo accionables cuando el titular es una persona. Un vencimiento tiene que decir **a quién hay que citar**, no cuántos faltan: con 129 trabajadores y 245 constancias, una bandeja que muestre el agregado no sirve para trabajar.

**Blocked by:** 06

**Type:** task

**Status:** resolved

- [x] La bandeja de vencimientos incluye las obligaciones de titular trabajador, mostradas a nivel de persona y no del agregado.
- [x] Cada caso de la bandeja identifica al trabajador al que corresponde.
- [x] La bandeja de pendientes de validación identifica al trabajador de cada evidencia.
- [x] Se puede filtrar por trabajador, además de por centro de costo, estado de cumplimiento, tipo de centro y obligación.
- [x] Los filtros preservan la distinción entre `Sin evidencia`, `Vencido` y `Pendiente de validación`.
- [x] Desde cada resultado se abre el trabajador, el centro de costo, la obligación y la evidencia sin perder contexto.
- [x] Las franquicias siguen fuera del conjunto operable y no se incluyen silenciosamente en los resultados.
- [x] La interfaz permanece server-rendered y usa HTMX solo para interacciones puntuales, con el mismo comportamiento sin JavaScript.
- [x] El umbral de «por vencer» sigue siendo el configurado y la bandeja sigue mostrando el valor activo.
- [x] Las bandejas siguen respondiendo con la escala real del piloto, sin degradarse al enumerar por persona.
