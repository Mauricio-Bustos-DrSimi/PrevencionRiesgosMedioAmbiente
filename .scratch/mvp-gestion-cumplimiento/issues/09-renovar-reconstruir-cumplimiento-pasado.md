# 09: Renovar evidencia y reconstruir el cumplimiento pasado

**What to build:** Un Prevencionista puede renovar una obligación mediante una evidencia nueva sin reemplazar la anterior, y puede reconstruir el estado de cumplimiento del centro de costo en una fecha seleccionada.

**Blocked by:** 08: Mostrar vencimientos y trabajo pendiente.

**Status:** resolved

- [x] Una obligación Vencida acepta la carga y validación de una evidencia nueva.
- [x] La renovación vuelve a producir el estado de cumplimiento que corresponda a la nueva vigencia.
- [x] La evidencia anterior permanece disponible e inalterada después de la renovación.
- [x] Un Prevencionista puede consultar el estado de cumplimiento calculado para una fecha pasada.
- [x] La reconstrucción considera el plan de aplicación, las versiones de la obligación, las validaciones y las vigencias que existían en esa fecha.
- [x] La consulta distingue correctamente periodos Sin evidencia, Vigente, Por vencer, Vencido, Pendiente de validación y No aplica.
- [x] Una prueba HTTP demuestra un ciclo completo de vigencia, vencimiento y renovación sin modificar registros anteriores.

## Answer

Implementado en el commit `281d3a4`.

La renovación de una obligación vencida carga y valida una evidencia nueva sin
tocar la anterior, que permanece disponible e inalterada. La reconstrucción a una
fecha pasada considera el plan de aplicación, las versiones de la obligación, las
validaciones y las vigencias que existían en ese momento, distinguiendo Sin
evidencia, Vigente, Por vencer, Vencido, Pendiente de validación y No aplica.

Cobertura: `evidencias/tests/test_renovacion_http.py` y
`planes_aplicacion/tests/test_historial_cumplimiento_http.py`.
