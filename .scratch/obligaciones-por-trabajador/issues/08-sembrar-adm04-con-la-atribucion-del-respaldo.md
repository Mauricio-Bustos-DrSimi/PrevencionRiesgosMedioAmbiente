# 08: Sembrar ADM04 con la atribución del respaldo

**What to build:** Que la siembra del piloto cargue las **245 constancias** de la carpeta, cada una a nombre del trabajador cuyo RUT nombra su carpeta, dando de alta a las 129 personas con el cargo que declara el nivel que las contiene. Hoy carga 18: una por obligación, la que caduca primero, colgada del centro de costo.

El titular de cada obligación pasa a salir del catálogo en vez de fijarse a mano: los catorce tipos de documento del respaldo son obligaciones del trabajador.

**Blocked by:** 02, 03, 05

**Type:** task

**Status:** resolved

- [x] El titular de cada obligación sale del catálogo, obligación por obligación; la siembra ya no lo fija a centro de costo para todo.
- [x] Los catorce tipos de documento del respaldo nacen como obligaciones de titular trabajador.
- [x] Se cargan todas las constancias del respaldo, no solo la que caduca primero de cada obligación.
- [x] Cada constancia queda atribuida al trabajador cuyo RUT nombra su carpeta.
- [x] Los trabajadores que aparecen en el respaldo se dan de alta, con el cargo que declara el nivel de carpeta que los contiene.
- [x] Una misma persona que aparece en varios cursos se reconoce como un solo trabajador.
- [x] Sembrar con atribución por persona **sin la carpeta original falla con ese motivo**, y no degrada en silencio a la carga por centro de costo.
- [x] El resumen versionado del respaldo sigue sin contener nombres ni RUT.
- [x] Las 87 constancias sin fecha legible se cargan pendientes de validación, una por persona, para resolverse con el mecanismo de corrección.
- [x] La siembra sigue exigiendo confirmación explícita y sigue negándose a sembrar dos veces el mismo centro de costo.
- [x] La periodicidad y la norma de origen siguen declaradas **preliminares** en el motivo de cada obligación sembrada.
- [x] La siembra completa termina en un tiempo razonable con las 245 constancias y sus archivos.
- [x] El procedimiento y sus límites quedan actualizados en la documentación del piloto, incluido que el límite del grano ya no existe.
