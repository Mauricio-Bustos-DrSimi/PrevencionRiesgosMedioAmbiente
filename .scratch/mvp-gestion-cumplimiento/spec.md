# MVP de gestión de cumplimiento por centro de costo

Status: ready-for-agent

## Problem Statement

El Departamento de Prevención de Riesgos necesita gestionar diariamente las obligaciones de seguridad y salud ocupacional y medio ambiente que aplican a cada centro de costo de Farmacias de Similares Chile, y demostrar ante una fiscalización qué se cumplió, mediante qué evidencia, quién actuó y cuándo.

Hoy el catálogo de obligaciones vive en fuentes Excel separadas y el seguimiento no ofrece una trazabilidad integrada. Esto dificulta distinguir una obligación nunca acreditada de una cuya evidencia venció, reconstruir el estado de cumplimiento en una fecha pasada y comprobar que un archivo no fue alterado. El problema debe resolverse en el grano de cada centro de costo, sin agregar resultados por encima de ese nivel ni confundir el código contable oficial con referencias cruzadas provenientes de otros sistemas.

El MVP debe cubrir el catálogo de obligaciones, los centros de costo, los planes de aplicación individuales, la carga y validación de evidencia, el cálculo de vigencias y estados de cumplimiento, la bandeja operativa y la bitácora append-only. Se probará primero con 8 a 10 centros de costo heterogéneos y será operado exclusivamente por el Departamento de Prevención de Riesgos.

## Solution

Construir una aplicación web operacional en Django sobre PostgreSQL, con plantillas server-rendered y HTMX para interacciones puntuales. El sistema mantendrá un catálogo versionado de obligaciones y un plan de aplicación independiente para cada centro de costo. Una evidencia se cargará como una entidad separada de la obligación, conservará su archivo en disco y registrará su hash SHA-256.

La evidencia comenzará como Pendiente de validación y solo dará cumplimiento cuando un Prevencionista confirme que corresponde a la obligación y que sus fechas son correctas. A partir de la periodicidad, la vigencia, el plan de aplicación y la validación, el sistema derivará uno de seis estados de cumplimiento: Vigente, Por vencer, Vencido, Pendiente de validación, Sin evidencia o No aplica. El estado nunca se ingresará manualmente.

El panel de administración de Django servirá para la mantención de datos maestros por Prevencionistas y Sysadmin. Las pantallas propias cubrirán la operación diaria: carga, validación, consulta por centro de costo y bandeja de vencimientos. Todas las acciones relevantes se conservarán en una bitácora append-only independiente del registro administrativo de Django.

## User Stories

1. Como Prevencionista, quiero iniciar sesión con una cuenta local, para acceder a las funciones del MVP según mis permisos.
2. Como Sysadmin, quiero administrar cuentas locales y su pertenencia a los grupos autorizados, para controlar quién opera el MVP.
3. Como Departamento de Prevención de Riesgos, quiero que las acciones estén asociadas a una identidad individual, para demostrar quién actuó.
4. Como Prevencionista, quiero consultar todos los centros de costo incluidos en el piloto, para operar sobre la instalación correcta.
5. Como Sysadmin, quiero cargar inicialmente centros de costo en forma masiva, para evitar una mantención manual uno por uno.
6. Como Prevencionista, quiero identificar cada centro de costo mediante su código contable oficial, para usar la identidad canónica de la instalación.
7. Como Prevencionista, quiero conservar `CveUnidad` como referencia cruzada opcional, para relacionar el centro de costo con `dw_chile` sin convertirla en su identidad.
8. Como Prevencionista, quiero clasificar un centro de costo como farmacia, centro administrativo o bodega, para disponer de contexto operativo y sugerencias iniciales.
9. Como Departamento de Prevención de Riesgos, quiero excluir las franquicias de forma declarada, para que su ausencia del sistema no se interprete como una omisión.
10. Como Prevencionista, quiero consultar el catálogo de obligaciones vigente, para conocer las exigencias normativas administradas por el sistema.
11. Como Prevencionista, quiero registrar una obligación con su norma de origen, titular de obligación y periodicidad, para preservar el fundamento de su cumplimiento.
12. Como Prevencionista, quiero incorporar al catálogo la información de las fuentes Excel actuales, para migrar la operación al sistema.
13. Como Prevencionista, quiero corregir una obligación mediante una nueva versión, para conservar lo que estuvo vigente anteriormente.
14. Como Prevencionista, quiero cerrar una obligación indicando fecha, autor y motivo, para reflejar un cambio normativo sin borrar evidencia pasada.
15. Como Fiscalizador, quiero conocer la norma de origen de una obligación, para relacionar la evidencia exhibida con la exigencia que acredita.
16. Como Prevencionista, quiero partir de una sugerencia de obligaciones basada en el tipo de centro de costo, para acelerar la configuración inicial.
17. Como Prevencionista, quiero confirmar individualmente el plan de aplicación de cada centro de costo, para que la aplicabilidad no dependa automáticamente de su tipo.
18. Como Prevencionista, quiero agregar una obligación al plan de aplicación de un centro de costo, para registrar que esa exigencia le corresponde.
19. Como Prevencionista, quiero declarar que una obligación no aplica a un centro de costo, para obtener el estado de cumplimiento No aplica con fundamento explícito.
20. Como Prevencionista, quiero indicar autor, fecha y motivo en cada cambio del plan de aplicación, para mantener trazabilidad comprobable.
21. Como Fiscalizador, quiero reconstruir qué obligaciones integraban el plan de aplicación en una fecha pasada, para evaluar el cumplimiento con el contexto que existía entonces.
22. Como Prevencionista, quiero localizar una obligación aplicable dentro de un centro de costo, para cargar su evidencia sin ambigüedad.
23. Como Prevencionista, quiero cargar una evidencia con su archivo, emisor y fechas, para acreditar una obligación concreta.
24. Como Prevencionista, quiero que una evidencia recién cargada quede Pendiente de validación, para evitar que produzca cumplimiento antes de confirmar sus datos.
25. Como Prevencionista, quiero validar que una evidencia corresponde a su obligación y que sus fechas son correctas, para permitir que produzca cumplimiento.
26. Como Departamento de Prevención de Riesgos, quiero que una evidencia pendiente cuente como no cumplida, para no sobreestimar el nivel real de cumplimiento.
27. Como Prevencionista, quiero incorporar una evidencia nueva sin reemplazar la anterior, para conservar la secuencia completa de renovaciones.
28. Como Fiscalizador, quiero acceder a las evidencias anteriores, para comprobar el cumplimiento durante periodos pasados.
29. Como Departamento de Prevención de Riesgos, quiero impedir la edición o eliminación destructiva de obligaciones, planes y evidencias, para preservar una historia append-only.
30. Como Sysadmin, quiero corregir errores mediante operaciones trazables y no mediante sobrescritura, para que incluso las correcciones sean comprobables.
31. Como Fiscalizador, quiero comparar el archivo de evidencia con su hash SHA-256 registrado, para comprobar que el contenido exhibido es el que se cargó.
32. Como Departamento de Prevención de Riesgos, quiero conservar los archivos de evidencia indefinidamente por defecto, para sostener la trazabilidad en el tiempo.
33. Como Prevencionista, quiero que el sistema derive la vigencia desde las fechas de la evidencia y la periodicidad de la obligación, para evitar cálculos manuales inconsistentes.
34. Como Prevencionista, quiero ver Vigente cuando existe una evidencia validada dentro de su ventana de vigencia, para reconocer el cumplimiento actual.
35. Como Prevencionista, quiero ver Por vencer cuando una evidencia validada se aproxima al fin de su vigencia, para actuar antes de que caduque.
36. Como Prevencionista, quiero ver Vencido cuando existió una evidencia validada cuya vigencia terminó, para distinguir una renovación pendiente.
37. Como Prevencionista, quiero ver Sin evidencia cuando una obligación aplicable nunca fue acreditada, para distinguir una omisión inicial de un vencimiento.
38. Como Prevencionista, quiero ver Pendiente de validación cuando la evidencia más relevante todavía no ha sido validada, para priorizar mi trabajo.
39. Como Prevencionista, quiero ver No aplica cuando la obligación está excluida del plan de aplicación vigente, para evitar falsos incumplimientos.
40. Como Departamento de Prevención de Riesgos, quiero que el estado de cumplimiento cambie automáticamente con el paso del tiempo, para que la información permanezca vigente sin intervención manual.
41. Como Prevencionista, quiero consultar el estado de cumplimiento por centro de costo y obligación, para trabajar en el grano correcto del modelo.
42. Como Prevencionista, quiero filtrar la operación por estado de cumplimiento, tipo de centro de costo y obligación, para encontrar los casos que requieren acción.
43. Como Prevencionista, quiero una bandeja de evidencias pendientes de validación, para procesar las cargas que todavía no producen cumplimiento.
44. Como Prevencionista, quiero una bandeja de obligaciones vencidas y por vencer, para priorizar renovaciones.
45. Como Prevencionista, quiero abrir desde la bandeja el centro de costo, la obligación y su evidencia relacionada, para resolver el caso sin perder contexto.
46. Como Departamento de Prevención de Riesgos, quiero consultar el avance del piloto de 8 a 10 centros de costo heterogéneos, para validar el modelo antes de ampliar el acceso.
47. Como Departamento de Prevención de Riesgos, quiero completar al menos un ciclo de vencimiento y renovación durante el piloto, para demostrar que el comportamiento temporal funciona antes del despliegue amplio.
48. Como Fiscalizador, quiero reconstruir el estado de cumplimiento de un centro de costo en una fecha pasada, para verificar qué podía demostrarse en ese momento.
49. Como Fiscalizador, quiero consultar la bitácora de una obligación y sus evidencias, para conocer qué ocurrió, quién actuó, cómo y cuándo.
50. Como Departamento de Prevención de Riesgos, quiero que la bitácora cubra tanto las pantallas propias como el panel administrativo, para que ningún canal de modificación rompa la trazabilidad.
51. Como Sysadmin, quiero que mis propias acciones queden en la bitácora, para que mis permisos elevados no creen zonas sin trazabilidad.
52. Como Prevencionista, quiero operar la carga, validación y bandejas desde pantallas propias, para realizar el trabajo diario sin depender del panel administrativo.
53. Como Prevencionista, quiero mantener los datos maestros desde el panel administrativo durante el MVP, para evitar construir interfaces especializadas antes de validar el dominio.
54. Como usuario del sistema, quiero recibir respuestas claras cuando un archivo no puede almacenarse o verificarse, para no creer que una evidencia fue registrada cuando la operación falló.
55. Como Departamento de Prevención de Riesgos, quiero que la aplicación funcione dentro de la red interna, para operar desde los centros autorizados sin publicarla en Internet.
56. Como equipo de TI, quiero una aplicación con un solo cuerpo de código server-rendered, para reducir la carga de despliegue y mantención.
57. Como equipo de TI, quiero que el esquema, el código y las interfaces del dominio usen nomenclatura en español, para mantener coherencia con el vocabulario del proyecto.

## Implementation Decisions

- El MVP comprende los pasos 1 a 3 de la secuencia acordada: modelo de datos, catálogo de obligaciones, centros de costo, planes de aplicación, evidencia, vigencias, estados de cumplimiento y bandeja de vencimientos.
- La aplicación se implementará con Django, plantillas server-rendered y HTMX sobre una base PostgreSQL dedicada. No habrá SPA ni frontend separado.
- La aplicación se desplegará en el servidor interno previsto y no requerirá exposición a Internet.
- El modelo separará Obligación, Evidencia, Vigencia y aplicabilidad. El estado de cumplimiento será un resultado derivado y no una columna editable por los usuarios.
- El catálogo de obligaciones será versionado. Cerrar o corregir una obligación conservará la versión anterior, su autor, fecha y motivo.
- La periodicidad pertenecerá a la obligación. La evidencia aportará las fechas concretas desde las cuales se calcula la vigencia.
- El modelo reconocerá como titulares de obligación al centro de costo, trabajador, externo y empresa, aunque el MVP implementará la operación diaria solo para obligaciones cuyo titular sea el centro de costo.
- El centro de costo será el grano operativo. Su identidad canónica será el código contable oficial; `CveUnidad` será una referencia cruzada.
- Las franquicias quedarán excluidas mediante una condición explícita del dominio.
- Cada centro de costo tendrá su propio plan de aplicación. El tipo de centro de costo podrá producir una sugerencia inicial, pero no creará herencia ni cambios automáticos posteriores.
- Todo cambio del plan de aplicación conservará autor, fecha y motivo, y permitirá reconstruir la aplicabilidad en una fecha pasada.
- Una evidencia se asociará a una obligación aplicable y conservará emisor, fechas, archivo, hash SHA-256, autor de carga y datos de validación.
- Una evidencia nueva no sobrescribirá la anterior. La secuencia de evidencias se conservará de forma monótona y permitirá identificar cuál produce cumplimiento en cada momento.
- La carga y la validación serán actos separados, incluso cuando ambas sean realizadas por usuarios del Departamento de Prevención de Riesgos. Una evidencia Pendiente de validación no producirá cumplimiento.
- Los archivos se almacenarán en disco y su hash SHA-256 se registrará en PostgreSQL. La verificación del hash debe estar disponible como comportamiento del sistema.
- La retención de evidencias y archivos será indefinida por defecto. Las correcciones se expresarán mediante nuevos actos trazables, no mediante edición o eliminación destructiva.
- Los estados de cumplimiento serán exactamente Vigente, Por vencer, Vencido, Pendiente de validación, Sin evidencia y No aplica.
- La distinción entre Sin evidencia y Vencido se preservará en el modelo, la interfaz y las consultas.
- El umbral que determina Por vencer será una política configurable del sistema, aplicada uniformemente y visible para el Departamento de Prevención de Riesgos.
- La bitácora del dominio será append-only y registrará qué ocurrió, quién actuó, cómo y cuándo. Cubrirá acciones efectuadas tanto desde las pantallas propias como desde el panel administrativo.
- El registro administrativo incluido en Django no sustituirá la bitácora del dominio.
- El panel administrativo se usará en el MVP para datos maestros, cuentas, catálogo de obligaciones, centros de costo y configuración inicial de planes. Las pantallas propias se reservarán para consulta operativa, carga, validación y bandejas.
- Las cuentas serán locales y los permisos se modelarán mediante usuarios, grupos y permisos de Django. Durante el MVP operarán Prevencionistas y Sysadmin.
- La nomenclatura del esquema, del código y de las interfaces del dominio será en español y respetará el vocabulario canónico.
- La carga inicial deberá admitir la incorporación controlada del catálogo existente y de los centros de costo del piloto, con reporte de filas aceptadas y rechazadas y sin crear duplicados silenciosos.
- El piloto incluirá entre 8 y 10 centros de costo heterogéneos: varias farmacias, un centro administrativo y una bodega.
- El MVP se considerará validado funcionalmente cuando el piloto complete un ciclo observable de vencimiento y renovación sin perder evidencia ni trazabilidad.

## Testing Decisions

- Una buena prueba verificará comportamiento observable mediante interfaces públicas. No dependerá de nombres internos de clases, consultas concretas, estructura privada de servicios ni detalles de plantillas que no afecten al usuario.
- El seam principal será una prueba de integración end-to-end mediante el cliente HTTP de Django. Recorrerá la configuración de un centro de costo y su plan de aplicación, la carga y validación de una evidencia, el estado de cumplimiento derivado y la consulta de la bitácora.
- El mismo seam controlará el tiempo para comprobar las transiciones Vigente, Por vencer y Vencido sin editar manualmente el estado de cumplimiento.
- El recorrido principal comprobará que Pendiente de validación no produce cumplimiento y que la validación sí habilita el cálculo de vigencia.
- Se comprobará mediante la interfaz pública la diferencia entre Sin evidencia y Vencido.
- Se comprobará que No aplica depende del plan de aplicación vigente y que los cambios de aplicabilidad conservan autor, fecha y motivo.
- Se comprobará que una renovación agrega una evidencia y conserva la anterior, permitiendo reconstruir el estado de cumplimiento antes y después de la renovación.
- Se comprobará que el archivo recuperado coincide con el hash SHA-256 registrado y que una alteración puede detectarse.
- Se comprobará que las operaciones destructivas sobre entidades trazables no están disponibles como comportamiento autorizado y que las correcciones dejan nuevos actos en la bitácora.
- Se comprobará que las acciones realizadas desde las pantallas propias y desde el panel administrativo producen entradas equivalentes en la bitácora del dominio.
- Se comprobará la autorización de Prevencionista y Sysadmin desde las respuestas HTTP y los efectos observables, no inspeccionando directamente la implementación de permisos.
- Las pruebas de archivos usarán almacenamiento temporal aislado y limpiarán sus propios artefactos al terminar.
- Las pruebas que dependan de comportamiento propio de PostgreSQL se ejecutarán contra PostgreSQL, no contra un motor alternativo.
- Las importaciones iniciales se probarán con filas válidas, duplicadas y rechazables, verificando el resultado reportado y los datos observables creados.
- No existe código de aplicación ni suite de pruebas previa en el proyecto. Por tanto, no hay prior art reutilizable; el seam HTTP aprobado será el patrón inicial para las pruebas posteriores.

## Out of Scope

- Apertura del sistema a los Encargados de centro de costo.
- Acceso operativo para el rol Lector y vistas agregadas para gerencia o jefaturas zonales.
- Jerarquía zonal.
- Importación o mantención de trabajadores, obligaciones cuyo titular sea un trabajador, ODI, entrega de EPP, exámenes ocupacionales y capacitaciones por persona.
- Integración automática con RRHH.
- Gestión de externos, verificaciones por empresa o faena y flujos asociados a la Ley 20.123.
- Operación de obligaciones cuyo titular sea la empresa, incluida la declaración anual de Ley REP.
- Reimplementación del cálculo de Ley REP actualmente resuelto fuera del sistema.
- Modelado completo de IPER; en el alcance actual solo puede existir como la obligación de mantener una evidencia vigente.
- Notificaciones por correo para Encargados o Prevencionistas.
- Pantalla propia para construir planes de aplicación; durante el MVP su mantención se apoya en el panel administrativo.
- SPA, frontend separado, aplicación móvil o API pública.
- Publicación de la aplicación fuera de la red interna.
- Capa de reporte gerencial en Power BI.
- Política definitiva de ciclo de vida de cuentas locales, incluidas caducidad, recuperación, revisión periódica y desactivación por egreso.
- Definición del modelo operativo de soporte posterior al MVP.

## Further Notes

- Las decisiones de separar Obligación y Evidencia, conservar registros append-only y derivar el estado de cumplimiento provienen del ADR 0001 y son restricciones arquitectónicas, no preferencias de implementación.
- La aplicación web propia sobre PostgreSQL y el almacenamiento de archivos con hash SHA-256 provienen del ADR 0002.
- Django con plantillas server-rendered y HTMX, el uso del panel administrativo para datos maestros y la necesidad de una bitácora de dominio propia provienen del ADR 0003.
- La meta vigente es llevar el MVP a producción durante el primer trimestre de 2027.
- La apertura posterior a los aproximadamente 350 centros de costo no debe ocurrir hasta que el piloto complete un ciclo de vencimiento y renovación.
- Antes de implementar autenticación más allá de la configuración mínima del piloto, debe cerrarse la política de ciclo de vida de cuentas locales.
- El respaldo coordinado de la base PostgreSQL y del directorio de archivos del servidor todavía debe confirmarse. Ambos forman una sola unidad de recuperación para fines de trazabilidad.
- La responsabilidad de soporte en producción sigue sin definirse y deberá resolverse antes de ampliar el acceso fuera del Departamento de Prevención de Riesgos.
