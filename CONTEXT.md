# Prevención de Riesgos y Medio Ambiente

Sistema integral de gestión de riesgos para los centros de costo de Farmacias de Similares (Chile), con trazabilidad comprobable ante fiscalización. Cubre dos familias normativas: seguridad y salud ocupacional (Ley 16.744, DS 594, DS 44) y medio ambiente.

## Language

**Centro de costo**:
Unidad organizacional sobre la que se gestiona y se responde individualmente ante fiscalización. Es el grano de todo el modelo: nada se agrega por encima de él sin decirlo explícitamente. Sus tipos son farmacia, centro administrativo y bodega. Se identifica por su **código contable oficial**; el `CveUnidad` de `dw_chile` es solo una referencia cruzada. No confundir con el uso contable amplio del término, donde "centro de costo" designa un área funcional (VENTAS, FRANQUICIA): aquí siempre es una instalación física individual.
_Avoid_: sucursal, local, unidad, tienda, área

**Obligación**:
Exigencia normativa permanente que recae sobre un titular (por ejemplo ODI, entrega de EPP, examen ocupacional, extintor certificado, comité paritario, declaración Ley REP). Existe con independencia de si se ha cumplido o no, y no todas aplican a todos los titulares.
_Avoid_: requisito, tarea, ítem, checklist

**Titular de obligación**:
Entidad sobre la que recae una obligación. Hay cuatro: centro de costo, trabajador, externo y **empresa** (obligaciones corporativas como la declaración anual de Ley REP, que no pertenecen a ninguna instalación). Centro de costo y trabajador están implementados; externo y empresa son pasos posteriores y se rechazan explícitamente. El titular lo declara la obligación, y de él depende contra quién se carga la evidencia.
_Avoid_: responsable, dueño

**Catálogo de obligaciones**:
Conjunto versionado de todas las obligaciones conocidas, con su norma de origen y su periodicidad. Vive dentro del sistema, no en un Excel paralelo: cuando una norma cambia, la obligación se cierra con fecha y autor, sin borrar la evidencia que la probó.
_Avoid_: matriz legal, listado

**Evidencia**:
Documento concreto que prueba el cumplimiento de una obligación en un momento dado, con su archivo respaldatorio, su emisor y su fecha. Se carga **contra un titular**: si la obligación es del trabajador, acredita a una persona identificada por su RUT; si es del centro de costo, acredita a la instalación. El centro de costo siempre está —es el contexto operativo— pero no siempre es el titular. La evidencia caduca; la obligación no.
_Avoid_: certificado, respaldo, adjunto, documento

**Corrección de evidencia**:
Registro append-only con las fechas verdaderas que Prevención leyó en un documento que no las declaraba —un escaneo sin capa de texto—, con su autor y su motivo. No modifica la evidencia: el archivo es el mismo y su hash sigue siendo el que se calculó al cargarlo. La vigencia se deriva de la corrección más reciente anterior a la fecha consultada. Corregir es distinto de renovar: no llegó otro documento, se leyó bien el que ya estaba.
_Avoid_: edición, ajuste, rectificación

**Vigencia**:
Ventana de tiempo durante la cual una evidencia mantiene cumplida su obligación. El estado de cumplimiento se deriva de la vigencia; nunca se teclea a mano.
_Avoid_: estado, validez, cumplimiento

**Externo**:
Empresa contratista o subcontratista que ejecuta trabajos en instalaciones de Similares Chile. Es un titular de obligaciones distinto del centro de costo: la obligación es suya, y lo que Similares registra es la verificación de que la cumplió (Ley 20.123).
_Avoid_: proveedor, tercero, contratista externo

**Plan de aplicación**:
Conjunto de obligaciones que aplican a un sujeto determinado: un centro de costo o un trabajador. Se define individualmente para cada uno y no se hereda —ni del tipo de centro, ni del cargo—; el tipo y el cargo solo sugieren.
_Avoid_: checklist, matriz, plantilla

**Estado agregado**:
Lo que un centro de costo muestra para una obligación cuyo titular es el trabajador: el **peor estado presente** entre las personas de su dotación a las que la obligación aplica, más cuántas hay en cada estado. Se muestra así para que una sola persona sin cobertura no quede escondida detrás del promedio, y siempre se puede abrir el desglose para saber cuáles. Un centro sin ningún trabajador aplicable resulta No aplica.
_Avoid_: resumen, consolidado, porcentaje de cumplimiento

**Periodicidad**:
Cada cuánto debe renovarse la evidencia de una obligación (anual, bienal, por evento, permanente). Es atributo de la obligación, no de la evidencia.
_Avoid_: frecuencia, vencimiento

**Estado de cumplimiento**:
Valor derivado de la vigencia y del plan de aplicación: Vigente, Por vencer, Vencido, Pendiente de validación, Sin evidencia o No aplica. "Sin evidencia" (nunca se hizo) y "Vencido" (se dejó caer) son faltas distintas y nunca se colapsan en una sola. "Pendiente de validación" cuenta como no cumplido.
_Avoid_: semáforo, status

**Trabajador**:
Persona contratada por Similares Chile, asignada a un centro de costo, y **titular efectivo** de obligaciones propias (ODI, entrega de EPP, examen ocupacional, capacitación, licencia de conducir). Se identifica por su **RUT**, normalizado a una sola forma canónica; el nombre es un atributo y no la identidad. Su pertenencia a un centro de costo es histórica y append-only, no un campo que se sobreescribe. Nace no validado y no produce cumplimiento hasta que Prevención lo valida; la baja es un cierre con motivo, no un borrado.
_Avoid_: empleado, colaborador, personal

**Cargo**:
Función que una persona desempeña, y de la que se desprende la **sugerencia inicial** de sus obligaciones: un operador de maquinaria parte con licencia de conducir, examen de operadores y manejo de extintores. Es un atributo del trabajador, no una entidad con plan propio: la aplicabilidad no se hereda del cargo, se confirma persona por persona con autor, fecha y motivo. Cambiar el cargo de alguien no modifica por sí solo su plan ya confirmado.
_Avoid_: puesto, rol, perfil, categoría

**Encargado de centro de costo**:
Rol que carga la evidencia de su propio centro de costo. Ve su centro de costo y ningún otro.
_Avoid_: jefe de local, usuario

**Prevencionista**:
Rol que ve todos los centros de costo, valida la evidencia cargada y define los planes de aplicación. Pertenece al Departamento de Prevención de Riesgos.
_Avoid_: experto, supervisor

**Sysadmin**:
Rol que ejecuta cargas iniciales masivas, correcciones y gestión de usuarios. Sus acciones quedan en la bitácora igual que las de cualquier otro rol.
_Avoid_: administrador, superusuario

**Lector**:
Rol de solo lectura sobre el estado agregado (gerencia, jefaturas zonales). No carga ni valida.
_Avoid_: visor, invitado

**Validación**:
Acto por el cual un Prevencionista confirma que una evidencia cargada corresponde a su obligación y que sus fechas son correctas. Hasta que ocurre, la evidencia no da cumplimiento.
_Avoid_: aprobación, revisión

**Franquicia**:
Centro de costo operado por un franquiciado, que es otro empleador con otro RUT y responde por su propia prevención de riesgos. Queda **fuera del alcance** de este sistema por exclusión declarada, no por omisión.
_Avoid_: FRA, sucursal franquiciada

**Bitácora**:
Registro append-only de toda acción sobre el sistema: qué se hizo, quién lo hizo, cómo y cuándo. Alcanza a todos los roles, incluido Sysadmin. Es lo que convierte la evidencia en trazabilidad comprobable.
_Avoid_: log, auditoría, historial

**Departamento de Prevención de Riesgos**:
Área que opera y consume el sistema, con uso diario. Es el usuario primario; gerencia y fiscalizadores son audiencias secundarias.
_Avoid_: HSE, seguridad, área de riesgos
