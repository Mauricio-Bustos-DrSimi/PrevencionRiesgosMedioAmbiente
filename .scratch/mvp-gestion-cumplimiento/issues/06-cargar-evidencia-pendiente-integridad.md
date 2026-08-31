# 06: Cargar evidencia pendiente con integridad verificable

**What to build:** Un Prevencionista puede cargar una evidencia para una obligación aplicable. El sistema conserva emisor, fechas, archivo y hash SHA-256, presenta Pendiente de validación y responde claramente ante fallos sin afirmar que la operación terminó cuando no fue así.

**Blocked by:** 04: Configurar el plan de aplicación individual.

**Status:** resolved

- [x] Un Prevencionista puede seleccionar una obligación aplicable dentro del detalle de un centro de costo y cargar su evidencia.
- [x] La carga exige el archivo de evidencia, emisor y fechas necesarias para calcular posteriormente la vigencia.
- [x] El archivo queda almacenado en disco y su hash SHA-256 queda registrado con la evidencia.
- [x] Una evidencia recién cargada muestra Pendiente de validación y no produce cumplimiento.
- [x] No se permite cargar evidencia para una obligación cuyo estado de aplicabilidad sea No aplica.
- [x] Un fallo al almacenar el archivo o registrar los datos produce una respuesta clara y no deja una evidencia parcial.
- [x] La carga conserva autor y fecha y agrega el acto correspondiente a la bitácora del dominio.
- [x] Las pruebas usan almacenamiento temporal aislado y verifican el comportamiento mediante el cliente HTTP de Django.


## Answer

Implementado en el commit `a1aa1d2`.

El archivo se almacena bajo `MEDIA_ROOT` en disco del servidor y su hash SHA-256
queda registrado con la evidencia. Una evidencia recién cargada muestra
Pendiente de validación y no produce cumplimiento. No se permite cargar
evidencia sobre una obligación No aplica, y un fallo al almacenar produce una
respuesta clara sin dejar evidencia parcial.
