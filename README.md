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
.\.venv\Scripts\python.exe -m mypy acceso configuracion manage.py
```

La configuración normal sigue apuntando a PostgreSQL. Las capacidades que dependan de comportamiento específico de PostgreSQL deben validarse contra ese motor.
