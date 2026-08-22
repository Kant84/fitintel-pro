<#
.SYNOPSIS
    FitIntel Pro — Авто-деплой (Backend + Desktop Client)
.DESCRIPTION
    Устанавливает зависимости, чинит битые .py файлы, мигрирует enum-данные,
    запускает бэкенд и тонкий клиент.
    Запускать от имени Администратора.
.PARAMETER BackendPath
    Путь к бэкенду (где app/main.py)
.PARAMETER ClientPath
    Путь к тонкому клиенту (где main.py)
.PARAMETER SkipBackend
    Пропустить запуск бэкенда
.PARAMETER SkipClient
    Пропустить запуск клиента
#>
param(
    [string]$BackendPath = "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI",
    [string]$ClientPath  = "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop",
    [switch]$SkipBackend,
    [switch]$SkipClient,
    [switch]$FixOnly
)

$ErrorActionPreference = "Stop"
function Write-Step($msg) { Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] >>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)  { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERR] $msg" -ForegroundColor Red }

# ===== 1. Проверка Python =====
Write-Step "Проверка Python..."
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Err "Python не найден. Установите Python 3.10+"; exit 1 }
$ver = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Ok "Python $ver"

# ===== 2. Чинилка битых .py файлов =====
Write-Step "Проверка синтаксиса .py файлов клиента..."
$broken = @()
Get-ChildItem -Path $ClientPath -Recurse -Filter "*.py" | ForEach-Object {
    $null = python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" $_.FullName 2>$null
    if ($LASTEXITCODE -ne 0) { $broken += $_.FullName; Write-Warn "Битый: $($_.Name)" }
}
if ($broken.Count -gt 0) {
    Write-Step "Авто-ремонт $($broken.Count) файлов..."
    $fixPy = @'
import ast, sys, io

def fix(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for attempt in range(60):
        src = "\n".join(lines)
        try:
            ast.parse(src)
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(src)
            return f"FIXED ({attempt} склеек)"
        except SyntaxError as e:
            ln = e.lineno
            if ln is None or ln < 1 or ln > len(lines): return f"FAIL: {e}"
            idx = ln - 1
            if idx + 1 >= len(lines): return f"FAIL: {e}"
            lines[idx] = lines[idx] + "\n" + lines[idx + 1]
            del lines[idx + 1]
    return "FAIL: лимит"

for p in sys.argv[1:]:
    print(f"{p}: {fix(p)}")
'@
    $fixPath = Join-Path $ClientPath "fix_strings.py"
    Set-Content -Path $fixPath -Value $fixPy -Encoding UTF8
    python $fixPath @broken
    Remove-Item $fixPath
}
Write-Ok "Синтаксис .py файлов в порядке"

# ===== 3. Установка зависимостей =====
if (-not $FixOnly) {
    Write-Step "Установка зависимостей бэкенда..."
    Push-Location $BackendPath
    $env:PYTHONPATH = "."
    if (-not (Test-Path "venv")) { python -m venv venv }
    .\venv\Scripts\Activate.ps1
    pip install -q -r requirements.txt 2>$null
    Write-Ok "Зависимости бэкенда установлены"

    Write-Step "Установка зависимостей клиента..."
    Push-Location $ClientPath
    pip install -q PyQt6 requests 2>$null
    Write-Ok "Зависимости клиента установлены"
    Pop-Location
    Pop-Location
}

# ===== 4. Миграция enum-данных (если БД существует) =====
if (-not $FixOnly -and -not $SkipBackend) {
    Write-Step "Миграция данных в БД (enum-значения)..."
    $migratePy = @'
# -*- coding: utf-8 -*-
import sys, os
backend = sys.argv[1]
sys.path.insert(0, backend)
from sqlalchemy import text

engine = None
for mod in ("app.db.session", "app.core.database", "app.database"):
    try:
        m = __import__(mod, fromlist=["engine"])
        engine = getattr(m, "engine", None)
        if engine: break
    except Exception: continue

if not engine:
    print("Engine not found -- skipping migration")
    sys.exit(0)

with engine.begin() as c:
    for old, new in [("МУЖСКОЙ","MALE"),("ЖЕНСКИЙ","FEMALE"),("мужской","MALE"),("женский","FEMALE"),
                     ("М","MALE"),("Ж","FEMALE"),("m","MALE"),("f","FEMALE"),("male","MALE"),("female","FEMALE")]:
        c.execute(text("UPDATE clients SET gender=:new WHERE gender=:old"), {"old":old,"new":new})
    for old, new in [("ОБЫЧНАЯ","ADULT"),("ВЗРОСЛЫЙ","ADULT"),("обычная","ADULT"),("REGULAR","ADULT"),("regular","ADULT"),
                     ("РЕБЕНОК","CHILD"),("РЕБЁНОК","CHILD"),("child","CHILD"),
                     ("terminal","STAFF"),("staff","STAFF"),("vip","VIP")]:
        c.execute(text("UPDATE clients SET client_category=:new WHERE client_category=:old"), {"old":old,"new":new})
    c.execute(text("UPDATE clients SET status = UPPER(status) WHERE status <> UPPER(status)"))
    rows = c.execute(text("SELECT id FROM clients WHERE email IS NULL OR email NOT LIKE '%@%'")).all()
    for (cid,) in rows:
        c.execute(text("UPDATE clients SET email=:e WHERE id=:id"),
                  {"e": f"noemail-{str(cid)[:8]}@fitintel.local", "id": cid})
print("DB migration OK")
'@
    $migratePath = Join-Path $BackendPath "scripts\temp\auto_migrate.py"
    New-Item -ItemType Directory -Path (Split-Path $migratePath) -Force | Out-Null
    Set-Content -Path $migratePath -Value $migratePy -Encoding UTF8
    python $migratePath $BackendPath
    Write-Ok "Миграция БД завершена"
}

# ===== 5. Патч API клиента (login endpoint) =====
if (-not $FixOnly) {
    Write-Step "Патч API клиента (endpoint login)..."
    $clientPy = Join-Path $ClientPath "api\client.py"
    $src = Get-Content $clientPy -Raw -Encoding UTF8
    $src = $src -replace '"/auth/token"', '"/auth/login"'
    $src = $src -replace '"username": username', '"login": username'
    if ($src -notmatch '_as_list') {
        $helper = @"

    @staticmethod
    def _as_list(data):
        if isinstance(data, list): return data
        if isinstance(data, dict):
            for k in ("items","data","results","visits","clients","subscriptions","entries","users","devices"):
                if isinstance(data.get(k), list): return data[k]
        return []
"@
        $src = $src -replace '(    def _url\(self, path: str\) -> str:)', "$helper`n`$1"
    }
    Set-Content -Path $clientPy -Value $src -Encoding UTF8 -NoNewline
    Write-Ok "client.py пропатчен"
}

# ===== 6. Запуск бэкенда =====
if (-not $FixOnly -and -not $SkipBackend) {
    Write-Step "Запуск бэкенда..."
    Push-Location $BackendPath
    $env:PYTHONPATH = "."
    Start-Process -FilePath "python" -ArgumentList "-m","app.main" -WindowStyle Normal
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/health" -TimeoutSec 5
        Write-Ok "Бэкенд запущен на http://127.0.0.1:8001"
    } catch {
        Write-Warn "Бэкенд запущен, но health-check не прошел -- проверьте вручную"
    }
    Pop-Location
}

# ===== 7. Запуск клиента =====
if (-not $FixOnly -and -not $SkipClient) {
    Write-Step "Запуск тонкого клиента..."
    Push-Location $ClientPath
    Start-Process -FilePath "python" -ArgumentList "main.py" -WindowStyle Normal
    Write-Ok "Тонкий клиент запущен"
    Pop-Location
}

Write-Step "Деплой завершен!"
Write-Host "`nЛогин: my_new_username"
Write-Host "Пароль: TestPass123!"
Write-Host "`nЕсли окно не появилось -- проверьте консоль на ошибки."
