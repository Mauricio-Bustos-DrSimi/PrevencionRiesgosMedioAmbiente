param(
    [ValidateSet('Preparar','Plan','Migrar','Sembrar','Iniciar','DetenerPostgres')]
    [string]$Accion = 'Plan',
    [string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin'
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$local = Join-Path $raiz '.desarrollo-local\demo-mvp'
$datos = Join-Path $local 'postgres'
$python = Join-Path $raiz '.venv\Scripts\python.exe'
$variables = @{
    DJANGO_SETTINGS_MODULE='configuracion.settings'; DJANGO_TEST_USE_SQLITE='0'
    DJANGO_ENTORNO='demo'
    DJANGO_SECRET_KEY=[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    DJANGO_DEBUG='true'; DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost'
    DJANGO_MEDIA_ROOT=(Join-Path $local 'medios-demo'); DIAS_POR_VENCER='30'
    POSTGRES_DB='prevencion_desarrollo_demo'; POSTGRES_USER='demo_local'
    POSTGRES_PASSWORD=''; POSTGRES_HOST='127.0.0.1'; POSTGRES_PORT='55433'
    PGHOSTADDR=$null; PGSERVICE=$null; PGSERVICEFILE=$null; PGOPTIONS=$null
    PYTHONDONTWRITEBYTECODE='1'
}
$anteriores = @{}
function Ejecutar([string]$Programa, [string[]]$Argumentos) {
    & $Programa @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Fallo en $Programa ($LASTEXITCODE)" }
}
Push-Location $raiz
try {
    foreach ($nombre in $variables.Keys) {
        $anteriores[$nombre] = [Environment]::GetEnvironmentVariable($nombre, 'Process')
        [Environment]::SetEnvironmentVariable($nombre, $variables[$nombre], 'Process')
    }
    if ($Accion -eq 'Preparar') {
        if (Test-Path -LiteralPath $local) { throw 'La demo ya existe. No se sobrescribe.' }
        New-Item -ItemType Directory -Path $local | Out-Null
        Ejecutar (Join-Path $PostgresBin 'initdb.exe') @('-D',$datos,'-U','demo_local','--auth=trust','--encoding=UTF8','--locale=C')
    }
    if (!(Test-Path -LiteralPath (Join-Path $datos 'PG_VERSION'))) { throw 'Primero ejecutar Preparar.' }
    if ($Accion -eq 'DetenerPostgres') {
        Ejecutar (Join-Path $PostgresBin 'pg_ctl.exe') @('-D',$datos,'-m','fast','-w','stop')
        return
    }
    & (Join-Path $PostgresBin 'pg_ctl.exe') -D $datos status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Ejecutar (Join-Path $PostgresBin 'pg_ctl.exe') @('-D',$datos,'-l',(Join-Path $local 'postgres.log'),'-o','-h 127.0.0.1 -p 55433','-w','start')
    }
    $conexion = @('-h','127.0.0.1','-p','55433','-U','demo_local')
    $servidor = & (Join-Path $PostgresBin 'psql.exe') @conexion -d postgres -Atc 'SHOW data_directory'
    if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($servidor.Trim()) -ne [IO.Path]::GetFullPath($datos)) {
        throw 'Servidor ajeno al directorio de la demo.'
    }
    switch ($Accion) {
        'Preparar' { Ejecutar (Join-Path $PostgresBin 'createdb.exe') ($conexion + @('prevencion_desarrollo_demo')) }
        'Plan' { Ejecutar $python @('-B','manage.py','migrate','--plan') }
        'Migrar' { Ejecutar $python @('-B','manage.py','migrate','--noinput') }
        'Sembrar' {
            Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'sembrar-demo-local.py') | & $python -B -
            if ($LASTEXITCODE -ne 0) { throw 'Fallo en semilla ficticia.' }
        }
        'Iniciar' {
            if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
                throw 'El puerto 8000 ya esta ocupado; no se inicia otro Django.'
            }
            Ejecutar $python @('-B','manage.py','check')
            Ejecutar $python @('-B','manage.py','migrate','--check')
            $proceso = Start-Process -FilePath $python -ArgumentList '-B manage.py runserver 127.0.0.1:8000 --noreload' -WorkingDirectory $raiz -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $local 'django.log') -RedirectStandardError (Join-Path $local 'django-error.log')
            $listo = $false
            for ($intento = 0; $intento -lt 20; $intento++) {
                Start-Sleep -Milliseconds 500
                $listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
                if ($listener) {
                    $dueno = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
                    if ($dueno.ProcessId -ne $proceso.Id -and $dueno.ParentProcessId -ne $proceso.Id) {
                        throw 'El puerto 8000 pertenece a otro proceso.'
                    }
                    $respuesta = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/cuentas/iniciar-sesion/' -TimeoutSec 5
                    if ($respuesta.StatusCode -eq 200) { $listo = $true; break }
                }
            }
            if (!$listo) { throw 'Django no respondio. Revisar django-error.log.' }
            Write-Output "Django PID: $($listener.OwningProcess). URL verificada: http://127.0.0.1:8000/"
        }
    }
}
finally {
    foreach ($nombre in $anteriores.Keys) {
        [Environment]::SetEnvironmentVariable($nombre, $anteriores[$nombre], 'Process')
    }
    Pop-Location
}
