# scripts/stop_dev.ps1

# останавливаем выполнение скрипта при ошибке
$ErrorActionPreference = "SilentlyContinue"

# путь к pg_ctl.exe
$PgCtlPath = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"

# путь к каталогу данных PostgreSQL
$PgDataPath = "C:\pgsql\data"

Write-Host ""
Write-Host "=== FitNexus AI / DEV STOP ===" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------
# Шаг 1. Остановка python/uvicorn процесса
# ----------------------------------------------------------
Write-Host "[1/2] Остановка python.exe..." -ForegroundColor Yellow
taskkill /IM python.exe /F

# ----------------------------------------------------------
# Шаг 2. Остановка PostgreSQL
# ----------------------------------------------------------
Write-Host "[2/2] Остановка PostgreSQL..." -ForegroundColor Yellow
& $PgCtlPath -D $PgDataPath stop

Write-Host ""
Write-Host "Остановка завершена." -ForegroundColor Green