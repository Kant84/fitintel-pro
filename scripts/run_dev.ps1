# scripts/run_dev.ps1

# включаем остановку при ошибках
$ErrorActionPreference = "Stop"

# путь к корню проекта
$ProjectRoot = "C:\Users\PC\Desktop\2026\FitNexus AI\FitNexus AI"

# путь к PostgreSQL pg_ctl.exe
$PgCtlPath = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"

# путь к каталогу данных PostgreSQL
$PgDataPath = "C:\pgsql\data"

# путь к файлу логов PostgreSQL
$PgLogPath = "C:\Temp\pglogs\server5433.log"

# адрес и порт PostgreSQL для проверки доступности
$PgHost = "127.0.0.1"
$PgPort = 5433

# переходим в корень проекта
Set-Location $ProjectRoot

# активируем виртуальное окружение
. .\.venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "=== Шаг 1. Проверка PostgreSQL ===" -ForegroundColor Cyan

# проверяем, слушается ли порт PostgreSQL
$portCheck = netstat -ano | findstr ":$PgPort"

if (-not $portCheck) {
    Write-Host "PostgreSQL не слушает порт $PgPort. Запускаем..." -ForegroundColor Yellow

    # запускаем PostgreSQL
    & $PgCtlPath -D $PgDataPath -l $PgLogPath start

    # ждём несколько секунд, чтобы сервер успел подняться
    Start-Sleep -Seconds 3
}
else {
    Write-Host "PostgreSQL уже запущен на порту $PgPort." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Шаг 2. Повторная проверка PostgreSQL ===" -ForegroundColor Cyan

# повторно проверяем порт
$portCheckAfter = netstat -ano | findstr ":$PgPort"

if (-not $portCheckAfter) {
    Write-Host "Ошибка: PostgreSQL не поднялся на порту $PgPort." -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL доступен." -ForegroundColor Green

Write-Host ""
Write-Host "=== Шаг 3. Запуск FastAPI ===" -ForegroundColor Cyan

# запускаем FastAPI через python -m uvicorn
python -m uvicorn app.main:app --reload