# 10: Demostrar trazabilidad append-only de extremo a extremo

**What to build:** Un Fiscalizador puede consultar la secuencia completa de actos relacionados con una obligación y sus evidencias, verificar la integridad de los archivos y observar que las correcciones agregan información sin borrar ni sobrescribir lo anterior.

**Blocked by:** 09: Renovar evidencia y reconstruir el cumplimiento pasado.

**Status:** resolved

- [x] La bitácora presenta qué ocurrió, quién actuó, cómo y cuándo para cada acto relevante.
- [x] La consulta relaciona los cambios del centro de costo, obligación, plan de aplicación, evidencia y validación que forman el recorrido seleccionado.
- [x] Las acciones realizadas mediante el panel administrativo producen entradas de dominio equivalentes a las realizadas desde pantallas propias.
- [x] Las acciones de un Sysadmin quedan registradas con la misma trazabilidad que las de un Prevencionista.
- [x] Una corrección crea un nuevo acto o versión y conserva los datos previos consultables.
- [x] Las operaciones destructivas no están disponibles como comportamiento autorizado para registros trazables.
- [x] El sistema puede recalcular el hash SHA-256 de un archivo y mostrar si coincide con el valor registrado.
- [x] Las pruebas detectan una alteración del archivo y demuestran que el registro administrativo de Django no sustituye la bitácora del dominio.

## Answer

Se implementó el recorrido append-only por centro de costo y obligación, con relaciones explícitas hacia planes, evidencias y validaciones. El panel administrativo y las pantallas propias generan eventos de dominio equivalentes, incluidas las acciones de Sysadmin y los cambios de contraseña sin conservar secretos.

La verificación de integridad recalcula SHA-256, informa coincidencias o alteraciones y registra el acto. Las operaciones destructivas permanecen bloqueadas y las correcciones conservan las versiones anteriores. La cobertura de integración valida el recorrido completo, la detección de archivos alterados y la independencia respecto de `LogEntry` de Django.
