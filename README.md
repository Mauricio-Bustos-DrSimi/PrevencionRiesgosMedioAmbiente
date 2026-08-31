# Prevención de Riesgos y Medio Ambiente

Aplicación Django server-rendered para gestionar el cumplimiento por centro de costo de Farmacias de Similares Chile.

## Requisitos

- Python 3.12
- PostgreSQL

## Preparación local

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Configura las variables descritas en `.env.example` en el entorno de ejecución. La aplicación usa PostgreSQL de forma predeterminada y no carga automáticamente archivos `.env`.

Los archivos de evidencia se guardan bajo `MEDIA_ROOT`, que por omisión es `medios/` junto al código y se puede mover con `DJANGO_MEDIA_ROOT`. Con retención indefinida, ese directorio y la base son una sola unidad de respaldo.

`DIAS_POR_VENCER` define el umbral uniforme de la bandeja operativa; su valor predeterminado es 30 días y la propia bandeja muestra el valor activo.

Inicializa la base y crea el primer Sysadmin:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

La migración de la aplicación crea el grupo `Prevencionista`. Un Sysadmin puede crear cuentas locales y asignarlas a ese grupo desde el panel administrativo.

## Verificación

Las pruebas locales usan SQLite en memoria mediante una opción explícita porque no necesitan datos persistentes:

```powershell
$env:DJANGO_TEST_USE_SQLITE='1'
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m mypy acceso aceptacion bitacora centros_costo configuracion evidencias importaciones obligaciones planes_aplicacion manage.py
```

Los paquetes se enumeran de forma explícita: `mypy .` recorrería también `docs/`,
que contiene material que no es código.

La configuración normal sigue apuntando a PostgreSQL. Las capacidades que dependan de comportamiento específico de PostgreSQL deben validarse contra ese motor.

## Recorrido de aceptación del MVP

`manage.py test aceptacion` ejecuta el recorrido de aceptación: la demostración
reproducible del ciclo completo del piloto —configuración, carga, validación,
vencimiento, renovación, reconstrucción histórica, bitácora e integridad
SHA-256— a través de las interfaces HTTP.

Exige PostgreSQL y **se omite** si la base configurada es otra, de modo que una
ejecución sobre SQLite no puede confundirse con la demostración. Debe quedar
verde antes de ampliar el piloto. El procedimiento está en
[docs/recorrido-aceptacion-mvp.md](docs/recorrido-aceptacion-mvp.md).

## Piloto de la Bodega de Distribución

Dos comandos cargan el centro de costo ADM04 con el respaldo real del
departamento:

- `manage.py resumir_respaldo_bodega --carpeta <ruta>` lee la carpeta de
  constancias, extrae de cada PDF la fecha en que se realizó el curso y la
  fecha en que expira, y escribe un resumen por curso **sin nombres ni RUT**,
  que es lo único que entra al repositorio.
- `manage.py sembrar_demo_bodega --usuario <prevencionista>` siembra las
  obligaciones y su evidencia con esas fechas. Los estados de cumplimiento no
  se declaran: se derivan.

La periodicidad y la norma de origen de cada obligación son **preliminares** y
Prevención debe confirmarlas; son las que deciden si una constancia aparece
vigente o vencida. La siembra es irreversible, porque el modelo es append-only.
El procedimiento y sus límites están en
[docs/demo-bodega-distribucion.md](docs/demo-bodega-distribucion.md).
