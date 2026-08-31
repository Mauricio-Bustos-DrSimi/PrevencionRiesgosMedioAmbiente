# 03: Administrar el catálogo versionado de obligaciones

**What to build:** Un Prevencionista puede registrar y consultar obligaciones con su norma de origen, titular de obligación y periodicidad, y puede corregirlas o cerrarlas mediante nuevas versiones que conserven lo que estuvo vigente anteriormente.

**Blocked by:** 01: Iniciar la operación segura del MVP.

**Status:** resolved

- [x] Un Prevencionista puede registrar una obligación con norma de origen, titular de obligación y periodicidad.
- [x] El catálogo muestra la versión vigente de cada obligación y permite consultar sus versiones anteriores.
- [x] Corregir una obligación crea una nueva versión y conserva intacta la versión anterior.
- [x] Cerrar una obligación exige fecha, autor y motivo y evita que siga apareciendo como vigente.
- [x] El modelo reconoce centro de costo, trabajador, externo y empresa como titulares de obligación, aunque la operación del MVP solo habilita centro de costo.
- [x] No existe una operación autorizada que elimine destructivamente una obligación o sus versiones.
- [x] Cada alta, corrección y cierre produce una entrada en la bitácora del dominio.


## Answer

Implementado en el commit `009bdfe`, junto con el ticket 02.

El catálogo versiona cada obligación: corregir crea una versión nueva y conserva
intacta la anterior; cerrar exige fecha, autor y motivo. El modelo reconoce
centro de costo, trabajador, externo y empresa como titulares, aunque la
operación del MVP solo habilita centro de costo. No existe operación autorizada
que elimine destructivamente una obligación o sus versiones.
