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
5. **Paso del tiempo.** Con el reloj simulado, la misma evidencia recorre
   *Vigente* → *Por vencer* → *Vencido* en la bandeja de vencimientos, sin que
   nadie edite el estado.
6. **Renovación.** Una evidencia nueva restablece *Vigente*, la anterior sigue
   consultable y su archivo sigue en disco.
7. **Reconstrucción histórica.** La consulta por fecha pasada reproduce, para
   cada momento del ciclo, el estado de cumplimiento y la aplicabilidad que
   correspondían entonces.
8. **Bitácora e integridad.** El recorrido de trazabilidad explica qué ocurrió,
   quién actuó, cómo y cuándo, en ambos canales; la verificación SHA-256
   confirma los archivos intactos y **detecta uno alterado**.

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
.\.venv\Scripts\python.exe -m mypy acceso aceptacion bitacora centros_costo configuracion evidencias importaciones obligaciones planes_aplicacion manage.py
```

## Por qué exige PostgreSQL

El resto de la suite puede correr sobre SQLite en memoria
(`DJANGO_TEST_USE_SQLITE=1`) porque no depende del motor. El recorrido de
aceptación sí: es la comprobación de que el MVP funciona sobre el motor de
producción. Por eso **se omite en vez de pasar** cuando la base configurada no es
PostgreSQL, y lo informa con ese motivo. Una ejecución que reporte el recorrido
como omitido no sirve como demostración.
