# Recorrido de aceptación del MVP

El recorrido de aceptación es la demostración reproducible de que el piloto
puede operar un ciclo completo de cumplimiento sin perder evidencia ni
trazabilidad. **Debe quedar verde contra PostgreSQL antes de ampliar el piloto**
más allá de los centros de costo iniciales.

Vive en `aceptacion/tests/test_recorrido_mvp_http.py` y atraviesa las mismas
interfaces HTTP que usa el Departamento de Prevención de Riesgos: no llama a los
servicios por dentro ni escribe estados de cumplimiento a mano.

## Qué demuestra

El recorrido avanza en este orden, y cada paso se comprueba por lo que el
usuario ve:

1. **Autenticación.** Una visita anónima queda redirigida al inicio de sesión;
   el Prevencionista entra con su cuenta local y llega a la portada operativa.
2. **Configuración.** El Sysadmin da de alta el centro de costo y dos
   obligaciones desde el panel administrativo; el Prevencionista confirma la
   aplicabilidad de ambas con autor, fecha y motivo.
3. **Carga sin cumplimiento.** La evidencia recién cargada queda *Pendiente de
   validación* y se exhibe explícitamente como **no cumplida**: aparece en la
   bandeja de pendientes y no aparece entre las vigentes.
4. **Validación.** Al validarla, el estado *Vigente* se deriva solo. En el mismo
   acto una obligación se declara *No aplica*: deja de ofrecer carga de
   evidencia y, si el formulario se envía igual, el servidor la rechaza sin
   registrar nada.
5. **El trabajador como titular.** Se da de alta a dos personas con su RUT y su
   cargo; nacen **no validadas** y Prevención las incorpora. El plan individual
   de cada una se confirma persona por persona, partiendo de la sugerencia del
   cargo. Se comprueba que el mismo RUT escrito con puntos queda guardado en
   una sola forma canónica.
6. **Carga a nombre de una persona.** Una licencia de conducir no es de la
   farmacia. El intento de cargarla **sin indicar a quién acredita se rechaza**
   con ese motivo; con la persona indicada, la evidencia queda a su nombre y la
   bandeja de pendientes dice a quién citar.
7. **Corrección de fechas al validar.** El escaneo no declaraba sus fechas.
   Prevención las lee del papel y las escribe en el mismo envío en que valida:
   quedan **dos actos separados** en la bitácora, el archivo y su hash siguen
   siendo los de la carga, y la vigencia pasa a derivarse del dato confirmado.
   La pantalla muestra la fecha con que se cargó y la corregida.
8. **Estado agregado y desglose.** El plan del centro muestra, para esa
   obligación, el **peor estado presente** con su recuento —«Sin evidencia — 1
   de 2 trabajadores; Vigente: 1»— y desde ahí se abre el desglose por persona.
   La que sí tiene su licencia no esconde a la que no.
9. **Paso del tiempo.** Con el reloj simulado, la evidencia del centro y la de
   la persona recorren *Vigente* → *Por vencer* → *Vencido* en la bandeja de
   vencimientos, sin que nadie edite el estado. La bandeja identifica a la
   persona y se puede filtrar por ella.
10. **Renovación.** Una evidencia nueva restablece *Vigente* en los dos granos,
    la anterior sigue consultable y su archivo sigue en disco.
11. **Reconstrucción histórica.** La consulta por fecha pasada reproduce, para
    cada momento del ciclo, el estado de cumplimiento y la aplicabilidad que
    correspondían entonces.
12. **Traslado y baja.** La persona se traslada a otro centro de costo: deja de
    contar en el agregado del origen y cuenta en el del destino, pero lo que
    acreditó donde estaba sigue asociado a ese centro, y **la consulta a una
    fecha pasada usa la dotación de esa fecha**, no la de hoy. La baja es un
    cierre con motivo: deja de exigirse y no se borra nada.
13. **Bitácora e integridad.** El recorrido de trazabilidad explica qué ocurrió,
    quién actuó, cómo y cuándo, en ambos canales; el alta del trabajador, la
    corrección y la validación se leen como actos distintos; la verificación
    SHA-256 confirma los archivos intactos y **detecta uno alterado**.

## Cómo repetir la demostración

El recorrido usa un directorio temporal aislado para los archivos de evidencia y
lo limpia al terminar; no toca el almacenamiento de la instalación.

En PowerShell, apuntando a la PostgreSQL donde deba correr la demostración:

```powershell
$env:DJANGO_SECRET_KEY='reemplazar-por-un-valor-seguro'
$env:POSTGRES_DB='prevencion'
$env:POSTGRES_USER='prevencion'
$env:POSTGRES_PASSWORD='reemplazar-por-la-clave-de-postgresql'
$env:POSTGRES_HOST='127.0.0.1'
$env:POSTGRES_PORT='5432'

.\.venv\Scripts\python.exe manage.py test aceptacion
```

El rol de PostgreSQL necesita permiso para crear bases: Django levanta y destruye
`test_<POSTGRES_DB>` en cada ejecución, y no escribe en la base de la instalación.

Para dejar toda la suite verde antes de ampliar el piloto:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m mypy acceso aceptacion bitacora centros_costo configuracion evidencias importaciones obligaciones planes_aplicacion trabajadores manage.py
```

## Por qué exige PostgreSQL

El resto de la suite puede correr sobre SQLite en memoria
(`DJANGO_TEST_USE_SQLITE=1`) porque no depende del motor. El recorrido de
aceptación sí: es la comprobación de que el MVP funciona sobre el motor de
producción. Por eso **se omite en vez de pasar** cuando la base configurada no es
PostgreSQL, y lo informa con ese motivo. Una ejecución que reporte el recorrido
como omitido no sirve como demostración.
