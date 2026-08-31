# 11: Operar el conjunto de centros de costo del piloto

**What to build:** El Departamento de Prevención de Riesgos puede consultar el avance de 8 a 10 centros de costo heterogéneos, filtrar los casos por estado de cumplimiento, tipo y obligación y navegar desde una bandeja hasta el contexto necesario para actuar.

**Blocked by:** 05: Importar los datos iniciales del piloto; 08: Mostrar vencimientos y trabajo pendiente.

**Status:** resolved

- [x] El conjunto piloto contiene entre 8 y 10 centros de costo e incluye varias farmacias, un centro administrativo y una bodega.
- [x] Un Prevencionista puede consultar el estado de cumplimiento de cada obligación en el grano de un centro de costo.
- [x] La operación puede filtrarse por estado de cumplimiento, tipo de centro de costo y obligación.
- [x] Los filtros preservan la diferencia entre Sin evidencia, Vencido y Pendiente de validación.
- [x] Desde cada resultado se puede abrir el centro de costo, la obligación y la evidencia relacionada sin perder contexto.
- [x] Las franquicias no aparecen dentro del conjunto operable ni se incluyen silenciosamente en sus resultados.
- [x] La interfaz permanece server-rendered y usa HTMX solo para interacciones puntuales que mantengan el mismo comportamiento sin JavaScript.
- [x] Las pruebas verifican los filtros y la navegación con datos heterogéneos del piloto.

## Answer

Implementado en el commit `1f5b3e7`; la siembra del piloto real llegó en
`751295e` y `52dbf39`.

La operación del piloto filtra por estado de cumplimiento, tipo de centro de
costo y obligación sin confundir Sin evidencia, Vencido y Pendiente de
validación, y abre el centro, la obligación y la evidencia sin perder contexto.
Las franquicias quedan fuera del conjunto operable. La interfaz sigue siendo
server-rendered.

Cobertura: `evidencias/tests/test_operacion_piloto_http.py` verifica nueve
centros heterogéneos (siete farmacias, un centro administrativo y una bodega),
la exclusión de franquicias y el caso en que el piloto no se declara conforme.

La siembra `sembrar_demo_bodega` carga ADM04 con las fechas reales de las
constancias. La periodicidad y la norma de origen de esas obligaciones siguen
siendo **preliminares** y Prevención debe confirmarlas.
