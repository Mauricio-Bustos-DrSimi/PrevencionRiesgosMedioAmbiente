# Recuperación del entorno local

El proyecto requiere Python 3.12. No depende de que `py` lo encuentre: en
Windows puede localizarse bajo `$env:LOCALAPPDATA` (en la recuperación se usó
Python 3.12.3). El entorno anterior apuntaba a otro perfil local y se conserva
íntegro en `.desarrollo-local/venv-anterior/`.

## Recrear el entorno

Desde la raíz, con la aplicación detenida, verificar primero el intérprete:

```powershell
$python312 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
& $python312 -B --version
```

Si ya existe `.venv`, preservarlo antes de crear otro. No reutilizar un nombre
de respaldo existente:

```powershell
$raiz = (Get-Location).Path
$local = Join-Path $raiz '.desarrollo-local'
New-Item -ItemType Directory -Force -Path $local | Out-Null
$respaldo = Join-Path $local ('venv-' + [guid]::NewGuid().ToString('N'))
if (![IO.Path]::GetFullPath($respaldo).StartsWith($raiz + '\')) { throw 'Ruta fuera del proyecto' }
if (Test-Path -LiteralPath .venv) {
    Move-Item -LiteralPath (Join-Path $raiz '.venv') -Destination $respaldo
}
& $python312 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Falló venv' }
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Falló pip' }
.\.venv\Scripts\python.exe -m pip check
```

No se modifican las versiones declaradas en `requirements*.txt`. Sus rangos
permiten que una instalación futura resuelva otras versiones compatibles;
este procedimiento reproduce la preparación, no garantiza paquetes idénticos.

## Variables y comprobaciones

Django lee variables del proceso con `os.environ`. No carga `.env`
automáticamente. `scripts/pruebas-locales.ps1` establece las variables de prueba
y restaura sus valores anteriores al terminar; no lee `.env`.
La opción `-ExecutionPolicy Bypass` solo afecta al proceso PowerShell de esta
ejecución; no cambia la política persistente del equipo.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pruebas-locales.ps1 -Modo Comprobar
```

Comprueba Python 3.12, dependencias, configuración Django y sintaxis. Usa la
configuración SQLite en memoria, sin abrir ni migrar una base, y desactiva
la escritura de bytecode. No ejecuta la suite en este modo.

## PostgreSQL exclusivo de pruebas

Requiere binarios PostgreSQL locales; se verificó PostgreSQL 18.4:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pruebas-locales.ps1 -Modo Completa
# Si la ubicación o el puerto difieren:
# .\scripts\pruebas-locales.ps1 -Modo Completa -PostgresBin 'C:\ruta\bin' -Puerto 55433
```

Cada ejecución crea un clúster nuevo bajo `.desarrollo-local/pruebas-<id>/`,
lo inicia en `127.0.0.1:55432` y comprueba su `data_directory` antes de crear
la base `recuperacion_pruebas`. Si el puerto está ocupado, el arranque falla:
no se utiliza el servidor que lo ocupa. No inicia ni modifica servicios Windows.

El clúster emplea autenticación `trust`, exclusivamente para pruebas locales:
otros procesos de la máquina pueden conectarse mientras está iniciado.
No debe contener datos reales. Se detiene en `finally`, incluso si falla una
prueba; una interrupción forzada del proceso requiere revisar el clúster manualmente.

Se ejecuta mypy y después la suite completa, incluido el recorrido PostgreSQL.
Django crea y destruye `test_recuperacion_pruebas`; sus migraciones solo afectan
esa base nueva. La base vacía `recuperacion_pruebas` es la conexión administrativa
de las pruebas. No se ejecuta `manage.py migrate` sobre ninguna base existente.

`DJANGO_MEDIA_ROOT` apunta a `archivos-prueba` dentro de la ejecución aislada.
Las pruebas pueden crear sus propios directorios temporales y archivos sintéticos.
No se ejecutan comandos de siembra sobre documentos reales ni se lee `medios/`.
Los clústeres, logs y cachés se conservan localmente para diagnóstico y están
excluidos de Git, al igual que el entorno anterior.

## Resultado inicial de recuperación, 2026-09-08

- Entorno anterior preservado en `.desarrollo-local/venv-anterior/`.
- Python 3.12.3; PostgreSQL 18.4, clúster independiente detenido al finalizar.
- Instalados desde los requisitos originales: Django 5.2.17, psycopg 3.3.5,
  django-stubs 5.2.9 y mypy 1.19.1. `pip check` sin conflictos.
- Comprobación Django y sintaxis de 122 archivos correctas.
- Mypy: 122 archivos sin errores.
- Suite PostgreSQL: 122 pruebas en 64,900 segundos; 117 correctas y 5 fallidas,
  ninguna omitida. El recorrido de aceptación pasó. La base de pruebas fue
  destruida y el servidor aislado se detuvo pese al fallo de la suite.

Fallos observados en esa primera ejecución (corregidos posteriormente, ver abajo):

- `evidencias.tests.test_escala_bandejas.EscalaDeLasBandejasTests.test_la_bandeja_enumera_un_caso_por_persona_y_obligacion`: obtuvo 0 casos, esperaba 18.
- `trabajadores.tests.test_plan_del_trabajador.SugerenciaPorCargoTests`:
  `test_un_centro_sin_trabajadores_aplicables_resulta_no_aplica`,
  `test_un_trabajador_dado_de_baja_deja_de_exigirse`,
  `test_un_trabajador_no_validado_no_produce_cumplimiento` y
  `test_una_obligacion_excluida_del_plan_produce_no_aplica`: caso/agregado ausente.

El diagnóstico posterior confirmó consultas con `EN_FECHA = date(2026, 9, 1)`
y registros creados con el reloj actual: al simular el 1 de septiembre las cinco
pasaron; al simular el 2 fallaron, tanto en Santiago como en UTC. Cada una también
falló individualmente. La causa fue la incoherencia temporal de los datos de prueba.

## Corrección temporal de las pruebas, 2026-09-08

En `EscalaDeLasBandejasTests` y `SugerenciaPorCargoTests`, el `setUp()` activa
`aceptacion.reloj.reloj_en` antes de crear datos, a las 12:00 de `EN_FECHA`.
`timezone.make_aware` usa la zona configurada por Django y `enterContext`
restaura el reloj al terminar cada prueba, incluso si falla. La preparación
compartida queda así alineada con la consulta histórica de las cinco afectadas.

Se conservaron todos los cuerpos de prueba y sus expectativas. Continúan
explícitas la consulta del 01/09/2026, la emisión del 01/08/2026 y el vencimiento
del 01/08/2027. No se modificaron lógica de negocio ni utilidades temporales.

Validación TDD sobre PostgreSQL aislado:

- Antes del cambio: las cinco afectadas fallaron, en 0,856 segundos.
- Después del cambio: las mismas cinco pasaron, en 0,470 segundos.
- Suite completa: **122 pruebas correctas en 62,046 segundos, ninguna omitida**,
  incluido el recorrido de aceptación PostgreSQL.
- Django check: sin incidencias. Mypy: sin errores en 122 archivos.
- Sintaxis de 122 archivos y `pip check`: correctos.

La validación completa se ejecutó con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pruebas-locales.ps1 -Modo Completa
```

Cada ejecución utilizó un clúster nuevo; Django eliminó su base de pruebas y el
script detuvo PostgreSQL al finalizar. No se migraron bases existentes ni se
utilizaron documentos reales. No se hizo commit ni push.

## Verificación final del sistema visual, 2026-09-10

El ticket 7 añadió reflujo de escritorio para el ancho efectivo de un notebook
al 200 % de zoom. El sidebar permanece visible; la barra superior, los filtros,
los formularios, los KPI y la distribución cambian a una columna cuando el
espacio disponible lo requiere. Las tablas anchas conservan su desplazamiento
horizontal dentro de `.tabla-desplazable`.

Validación automatizada:

- `manage.py check`: sin incidencias.
- Mypy: 134 archivos sin errores.
- Pruebas focalizadas de layout, componentes, portada y operación: 43 correctas.
- Recorrido de aceptación afectado por la migración visual: correcto.
- Suite completa PostgreSQL: **158 pruebas correctas**, formada por las 122
  pruebas recuperadas originalmente y 36 pruebas incorporadas durante los
  tickets visuales. Django destruyó la base de pruebas y el script detuvo el
  clúster aislado al finalizar.
- `findstatic`: localizó los cinco CSS y el logotipo institucional. El SHA-256
  del archivo fuente y de la copia estática coincide.
- `git diff --check`: correcto; solo se informaron avisos de conversión futura
  de LF a CRLF.

Validación reproducible con Chrome local:

- Capturas de portada y operación a 1366 × 768 y 1920 × 1080 en
  `.desarrollo-local/ticket7-*.png`.
- Al 200 %, el documento midió 668 px tanto de ancho visible como de contenido:
  no hubo desplazamiento horizontal global y el sidebar siguió visible.
- En operación al 200 %, la tabla midió 1120 px dentro de un contenedor visible
  de 370 px con `overflow-x: auto`, por lo que el desplazamiento quedó interno.
- La primera pulsación de Tab enfocó “Saltar al contenido”, con contorno blanco
  sólido de 3 px, separación de 2 px y contraste superior a 3:1 sobre el
  sidebar; Enter trasladó el foco a `contenido-principal`.
- El recorrido de teclado visitó los 37 destinos enfocables de operación y los
  28 de portada, incluidos sidebar, seis filtros operativos, botones, KPI,
  contenedores de tabla y enlaces. Cada ciclo volvió al primer elemento, sin
  trampas, y todos los destinos conservaron un contorno sólido de 3 px.
- Con JavaScript deshabilitado se renderizaron portada y operación, los filtros
  GET conservaron sus valores seleccionados y ambos documentos contenían cero
  elementos `script`.
- El índice del admin respondió correctamente y las pruebas confirmaron que no
  carga los CSS ni el shell visual de la aplicación.

Las capturas contienen únicamente la semilla ficticia local. La aprobación
visual del usuario y la validación de claridad por una persona de Prevención
continúan siendo comprobaciones humanas posteriores.
