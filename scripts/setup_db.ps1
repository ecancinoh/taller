# setup_db.ps1 — Crea la base de datos PostgreSQL para TallerPro
# Uso: .\scripts\setup_db.ps1
# Requiere que PostgreSQL esté instalado y psql en el PATH

param(
    [string]$PgUser = "postgres",
    [string]$PgHost = "localhost",
    [string]$PgPort = "5432",
    [string]$DbName = "taller_mecanico_db"
)

Write-Host "=== TallerPro — Configuración de base de datos ===" -ForegroundColor Cyan

# Verificar que psql esté disponible
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    # Intentar encontrar psql en la ruta por defecto de PostgreSQL
    $pgPaths = @(
        "C:\Program Files\PostgreSQL\17\bin",
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\15\bin",
        "C:\Program Files\PostgreSQL\14\bin"
    )
    $found = $false
    foreach ($path in $pgPaths) {
        if (Test-Path "$path\psql.exe") {
            $env:Path += ";$path"
            Write-Host "PostgreSQL encontrado en: $path" -ForegroundColor Green
            $found = $true
            break
        }
    }
    if (-not $found) {
        Write-Host "ERROR: psql no encontrado. Instala PostgreSQL desde:" -ForegroundColor Red
        Write-Host "       https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Creando base de datos '$DbName'..." -ForegroundColor Yellow
$env:PGPASSWORD = Read-Host "Ingresa la contraseña de PostgreSQL para el usuario '$PgUser'" -AsSecureString | `
    ForEach-Object { [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) }

# Verificar si la BD ya existe
$exists = psql -U $PgUser -h $PgHost -p $PgPort -tAc "SELECT 1 FROM pg_database WHERE datname='$DbName';" postgres 2>&1
if ($exists -eq "1") {
    Write-Host "La base de datos '$DbName' ya existe." -ForegroundColor Green
} else {
    psql -U $PgUser -h $PgHost -p $PgPort -c "CREATE DATABASE $DbName ENCODING 'UTF8' LC_COLLATE 'Spanish_Chile.1252' LC_CTYPE 'Spanish_Chile.1252' TEMPLATE template0;" postgres 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Base de datos '$DbName' creada exitosamente." -ForegroundColor Green
    } else {
        # Intentar sin locale específico (funciona en cualquier sistema)
        psql -U $PgUser -h $PgHost -p $PgPort -c "CREATE DATABASE $DbName;" postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Base de datos '$DbName' creada exitosamente." -ForegroundColor Green
        } else {
            Write-Host "ERROR al crear la base de datos." -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "=== Aplicando migraciones Django ===" -ForegroundColor Cyan

$venvPython = Join-Path $PSScriptRoot "..\\.venv\\Scripts\\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: Entorno virtual no encontrado. Ejecuta primero:" -ForegroundColor Red
    Write-Host "       python -m venv .venv" -ForegroundColor Yellow
    Write-Host "       .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Push-Location (Join-Path $PSScriptRoot "..")
& $venvPython manage.py migrate
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Creando superusuario ===" -ForegroundColor Cyan
    & $venvPython manage.py createsuperuser
    Write-Host ""
    Write-Host "=== Todo listo! ===" -ForegroundColor Green
    Write-Host "Ejecuta: .venv\Scripts\python manage.py runserver" -ForegroundColor Yellow
    Write-Host "Accede a: http://127.0.0.1:8000/" -ForegroundColor Yellow
} else {
    Write-Host "ERROR en las migraciones. Verifica la configuración en .env" -ForegroundColor Red
}
Pop-Location
