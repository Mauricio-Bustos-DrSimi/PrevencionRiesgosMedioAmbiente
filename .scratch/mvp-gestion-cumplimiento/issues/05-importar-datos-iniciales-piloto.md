# 05: Importar los datos iniciales del piloto

**What to build:** Un Sysadmin puede incorporar centros de costo y obligaciones desde fuentes tabulares, obteniendo un resultado comprensible de filas aceptadas, rechazadas y duplicadas antes de operar el piloto.

**Blocked by:** 02: Registrar y consultar centros de costo; 03: Administrar el catálogo versionado de obligaciones.

**Status:** resolved

- [x] La importación acepta centros de costo identificados por código contable oficial y conserva `CveUnidad` solo como referencia cruzada.
- [x] La importación acepta obligaciones con norma de origen, titular de obligación y periodicidad válidos.
- [x] El resultado informa cuántas filas fueron aceptadas, rechazadas o detectadas como duplicadas y explica cada rechazo.
- [x] Una fila inválida no deja datos parciales ni impide reportar el resultado del resto del lote.
- [x] Repetir una importación no crea duplicados silenciosos.
- [x] Las franquicias se identifican y excluyen de la operación conforme a la regla del dominio.
- [x] Las altas realizadas por la importación quedan asociadas al Sysadmin y registradas en la bitácora del dominio.
- [x] Las pruebas cubren lotes con filas válidas, inválidas y duplicadas mediante la interfaz pública de importación.


## Answer

Implementado en el commit `554fef1`.

La importación acepta centros de costo y obligaciones desde fuentes tabulares e
informa filas aceptadas, rechazadas y duplicadas, explicando cada rechazo. Una
fila inválida no deja datos parciales ni interrumpe el reporte del resto del
lote, y repetir una importación no crea duplicados silenciosos. Las altas quedan
asociadas al Sysadmin y registradas en la bitácora del dominio.
