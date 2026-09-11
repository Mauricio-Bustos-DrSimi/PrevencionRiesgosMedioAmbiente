param(
    [ValidateSet('Comprobar', 'Completa')][string]$Modo = 'Comprobar',
    [string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin',
    [ValidateRange(1024, 65535)][int]$Puerto = 55432
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz '.venv\Scripts\python.exe'
$local = Join-Path $raiz '.desarrollo-local'
$ejecucion = Join-Path $local ('pruebas-' + [guid]::NewGuid().ToString('N'))
$datos = Join-Path $ejecucion 'postgres'
$arrancado = $false
$variables = @{
    DJANGO_SECRET_KEY = 'exclusiva-del-entorno-local-de-pruebas'
    DJANGO_DEBUG = 'false'
    DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,testserver'
    DJANGO_TEST_USE_SQLITE = '1'
    DJANGO_SETTINGS_MODULE = 'configuracion.settings'
    DJANGO_MEDIA_ROOT = (Join-Path $ejecucion 'archivos-prueba')
    DIAS_POR_VENCER = '30'
    POSTGRES_DB = 'recuperacion_pruebas'
    POSTGRES_USER = 'recuperacion'
    POSTGRES_PASSWORD = ''
    POSTGRES_HOST = '127.0.0.1'
    POSTGRES_PORT = "$Puerto"
    PYTHONDONTWRITEBYTECODE = '1'
    PGSERVICE = $null
    PGSERVICEFILE = $null
    PGOPTIONS = $null
    PGHOSTADDR = $null
}
$anteriores = @{}
function Ejecutar([string]$Programa, [string[]]$Argumentos) {
    & $Programa @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falló $Programa (salida $LASTEXITCODE)." }
}
Push-Location $raiz
try {
    foreach ($nombre in $variables.Keys) {
        $anteriores[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
        [Environment]::SetEnvironmentVariable($nombre, $variables[$nombre], 'Process')
    }
    Ejecutar $python @('-B', '-c', 'import sys; assert sys.version_info[:2] == (3, 12), sys.version')
    Ejecutar $python @('-B', '-m', 'pip', 'check')
    Ejecutar $python @('-B', 'manage.py', 'check')
    # Estas comprobaciones no crean bases ni leen archivos de evidencia.
    @'
import ast, pathlib, subprocess
paths = subprocess.check_output(['git', 'ls-files', '*.py'], text=True).splitlines()
for path in paths:
    ast.parse(pathlib.Path(path).read_text(encoding='utf-8-sig'), filename=path)
print('Sintaxis correcta:', len(paths), 'archivos')
'@ | & $python -B -
    if ($LASTEXITCODE -ne 0) { throw 'Fallo en la comprobacion de sintaxis.' }
    if ($Modo -eq 'Comprobar') { return }

    foreach ($binario in @('initdb.exe', 'pg_ctl.exe', 'psql.exe', 'createdb.exe')) {
        if (!(Test-Path -LiteralPath (Join-Path $PostgresBin $binario))) { throw "Falta $binario en $PostgresBin" }
    }
    # Un directorio nuevo por ejecución evita reutilizar cualquier base existente.
    New-Item -ItemType Directory -Path $ejecucion | Out-Null
    Ejecutar (Join-Path $PostgresBin 'initdb.exe') @('-D', $datos, '-U', 'recuperacion', '--auth=trust', '--encoding=UTF8', '--locale=C')
    # Trust se limita a este clúster desechable, escuchando únicamente en loopback.
    $arrancado = $true
    Ejecutar (Join-Path $PostgresBin 'pg_ctl.exe') @('-D', $datos, '-l', (Join-Path $ejecucion 'postgres.log'), '-o', "-h 127.0.0.1 -p $Puerto", '-w', 'start')
    $conexion = @('-h', '127.0.0.1', '-p', "$Puerto", '-U', 'recuperacion')
    $directorioServidor = & (Join-Path $PostgresBin 'psql.exe') @conexion -d postgres -Atc 'SHOW data_directory'
    if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($directorioServidor.Trim()) -ne [IO.Path]::GetFullPath($datos)) {
        throw 'La conexión no corresponde al clúster aislado esperado.'
    }
    Ejecutar (Join-Path $PostgresBin 'createdb.exe') ($conexion + @('recuperacion_pruebas'))
    $env:DJANGO_TEST_USE_SQLITE = '0'
    Ejecutar $python @('-B', '-m', 'mypy', '--cache-dir', (Join-Path $ejecucion 'mypy'), 'acceso', 'aceptacion', 'bitacora', 'centros_costo', 'configuracion', 'evidencias', 'importaciones', 'obligaciones', 'planes_aplicacion', 'trabajadores', 'manage.py')
    Ejecutar $python @('-B', 'manage.py', 'test', '--noinput')
}
finally {
    try {
        if ($arrancado) {
            # El intento de arranque puede fallar despues de crear el proceso.
            # pg_ctl stop actua solo sobre el PID de nuestro directorio exclusivo.
            & (Join-Path $PostgresBin 'pg_ctl.exe') -D $datos -m fast -w stop
            if ($LASTEXITCODE -ne 0 -and (Test-Path -LiteralPath (Join-Path $datos 'postmaster.pid'))) {
                throw "No se pudo detener el cluster aislado: $datos"
            }
        }
    }
    finally {
        foreach ($nombre in $anteriores.Keys) {
            [Environment]::SetEnvironmentVariable($nombre, $anteriores[$nombre], 'Process')
        }
        Pop-Location
    }
}
