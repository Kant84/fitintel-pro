# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Собирает контекст проекта FitIntel Pro Desktop для передачи нейросети.
.DESCRIPTION
    Создаёт файл _context_for_prompt.txt со всеми нужными фрагментами кода:
    API-клиент, users_tab, subscriptions_tab, roles_tab, form_dialog,
    FitIntelDesktop.spec, список assets, список permissions (если удалось получить).
.EXAMPLE
    .\collect_context.ps1
    .\collect_context.ps1 -OutFile "E:\temp\ctx.txt"
    .\collect_context.ps1 -SkipPermissions   # если нет доступа к БД
#>
param(
    [string]$OutFile = "_context_for_prompt.txt",
    [switch]$SkipPermissions
)

$ErrorActionPreference = "Continue"
$script:lines = New-Object System.Collections.Generic.List[string]

function W([string]$s = "") { $script:lines.Add($s) }
function H1([string]$s) {
    W ""
    W ("=" * 78)
    W "  " + $s
    W ("=" * 78)
    W ""
}
function H2([string]$s) {
    W ""
    W ("-" * 78)
    W "  " + $s
    W ("-" * 78)
    W ""
}

# ─── поиск корня проекта ───────────────────────────────────────────
function Find-ProjectRoot {
    $candidates = @(
        (Get-Location).Path,
        (Split-Path -Parent (Get-Location).Path)
    )
    foreach ($c in $candidates) {
        if ((Test-Path (Join-Path $c "fitintel-desktop")) -and
            (Test-Path (Join-Path $c "app"))) {
            return $c
        }
        if ((Test-Path (Join-Path $c "api\client.py")) -and
            (Test-Path (Join-Path $c "windows"))) {
            return (Split-Path -Parent $c)
        }
    }
    return $null
}

$root = Find-ProjectRoot
if (-not $root) {
    Write-Host "❌ Не найден корень проекта." -ForegroundColor Red
    Write-Host "   Запустите скрипт из папки fitintel-desktop/ или из корня репо."
    exit 1
}
$desktop = Join-Path $root "fitintel-desktop"
$app     = Join-Path $root "app"
Write-Host "✅ Корень проекта: $root" -ForegroundColor Green

# ─── 1. api/client.py ─────────────────────────────────────────────
H1 "1. api/client.py — методы ApiClient + хелперы"
$clientPath = Join-Path $desktop "api\client.py"
if (Test-Path $clientPath) {
    $content = Get-Content $clientPath -Raw -Encoding UTF8
    $lines = $content -split "`r?`n"
    W "  (полный файл, $($lines.Count) строк)"
    W ""
    W $content
    Write-Host "  ✓ api/client.py — $($lines.Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $clientPath"
}

# ─── 2. windows/users_tab.py ──────────────────────────────────────
H1 "2. windows/users_tab.py — полностью"
$usersPath = Join-Path $desktop "windows\users_tab.py"
if (Test-Path $usersPath) {
    $content = Get-Content $usersPath -Raw -Encoding UTF8
    W $content
    Write-Host "  ✓ windows/users_tab.py — $((Get-Content $usersPath).Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $usersPath"
}

# ─── 3. windows/subscriptions_tab.py ──────────────────────────────
H1 "3. windows/subscriptions_tab.py — полностью"
$subsPath = Join-Path $desktop "windows\subscriptions_tab.py"
if (Test-Path $subsPath) {
    $content = Get-Content $subsPath -Raw -Encoding UTF8
    W $content
    Write-Host "  ✓ windows/subscriptions_tab.py — $((Get-Content $subsPath).Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $subsPath"
}

# ─── 4. assets/ — список файлов (TTF/OTF) ─────────────────────────
H1 "4. assets/ — все файлы (для проверки шрифта DejaVuSans.ttf)"
$assetsDir = Join-Path $desktop "assets"
if (Test-Path $assetsDir) {
    $files = Get-ChildItem -Path $assetsDir -Recurse -File |
             Select-Object FullName, Length
    W "  Всего файлов: $($files.Count)"
    W ""
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($desktop.Length + 1)
        W ("  {0,8} байт  {1}" -f $f.Length, $rel)
    }
    W ""
    $ttf = Get-ChildItem -Path $assetsDir -Recurse -Include *.ttf, *.otf -ErrorAction SilentlyContinue
    if ($ttf) {
        W "  ✅ Найдены шрифты (для PDF кириллицы):"
        foreach ($t in $ttf) { W "     - $($t.Name) ($($t.Length) байт)" }
    } else {
        W "  ⚠ ШРИФТЫ TTF/OTF НЕ НАЙДЕНЫ."
        W "     Для экспорта PDF с кириллицей нужен assets/DejaVuSans.ttf."
    }
    Write-Host "  ✓ assets/ — $($files.Count) файлов" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН каталог: $assetsDir"
}

# ─── 5. windows/roles_tab.py ──────────────────────────────────────
H1 "5. windows/roles_tab.py — полностью"
$rolesPath = Join-Path $desktop "windows\roles_tab.py"
if (Test-Path $rolesPath) {
    $content = Get-Content $rolesPath -Raw -Encoding UTF8
    W $content
    Write-Host "  ✓ windows/roles_tab.py — $((Get-Content $rolesPath).Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $rolesPath"
}

# ─── 6. Список 51 разрешения ─────────────────────────────────────
H1 "6. Список 51 разрешения (permissions) — из БД"
if ($SkipPermissions) {
    W "  (пропущено — указан -SkipPermissions)"
} else {
    $sqlPath = Join-Path $env:TEMP "fitintel_perms.sql"
    @"
SELECT module || ' | ' || code || ' | ' || name AS "module | code | name"
FROM permissions
ORDER BY module, code;
"@ | Set-Content -Path $sqlPath -Encoding UTF8

    # вариант А: psql (если установлен)
    $psql = Get-Command psql -ErrorAction SilentlyContinue
    if ($psql) {
        try {
            W "  Пытаюсь через psql..."
            $env:PGPASSWORD = "fitnexus_user_password"   # ← ЗАМЕНИТЕ на реальный пароль
            $out = & psql -h localhost -U fitnexus_user -d fitnexus_ai -A -t -f $sqlPath 2>&1
            if ($LASTEXITCODE -eq 0 -and $out) {
                W "  ✅ Получено $($out.Count) строк:"
                W ""
                foreach ($row in $out) { W "  $row" }
                Write-Host "  ✓ permissions — $($out.Count) строк" -ForegroundColor Cyan
            } else {
                W "  ⚠ psql вернул ошибку: $out"
            }
        } catch {
            W "  ⚠ Ошибка psql: $($_.Exception.Message)"
        }
    } else {
        W "  ⚠ psql не найден в PATH."
    }

    # вариант Б: через docker exec (если psql не сработал)
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        try {
            W ""
            W "  Пытаюсь через docker exec..."
            $out2 = & docker exec deploy-db-1 psql -U fitnexus_user -d fitnexus_ai `
                    -A -t -f /tmp/fitintel_perms.sql 2>&1
            if ($LASTEXITCODE -eq 0 -and $out2) {
                W "  ✅ Получено $($out2.Count) строк:"
                W ""
                foreach ($row in $out2) { W "  $row" }
                Write-Host "  ✓ permissions (docker) — $($out2.Count) строк" -ForegroundColor Cyan
            } else {
                W "  ⚠ docker вернул: $out2"
            }
        } catch {
            W "  ⚠ Ошибка docker: $($_.Exception.Message)"
        }
    }

    # вариант В: из docs/RBAC (2).md, если есть
    $rbacDoc = Join-Path $root "docs\RBAC (2).md"
    if (Test-Path $rbacDoc) {
        W ""
        W "  Дополнительно: docs/RBAC (2).md (первые 500 строк)"
        W ""
        $md = Get-Content $rbacDoc -Encoding UTF8 -TotalCount 500
        foreach ($line in $md) { W "  $line" }
        Write-Host "  ✓ RBAC (2).md — $($md.Count) строк" -ForegroundColor Cyan
    } else {
        W "  ⚠ Не найден docs/RBAC (2).md"
    }
}

# ─── 7. windows/form_dialog.py ────────────────────────────────────
H1 "7. windows/form_dialog.py — полностью"
$formPath = Join-Path $desktop "windows\form_dialog.py"
if (Test-Path $formPath) {
    $content = Get-Content $formPath -Raw -Encoding UTF8
    W $content
    Write-Host "  ✓ windows/form_dialog.py — $((Get-Content $formPath).Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $formPath"
}

# ─── 8. FitIntelDesktop.spec — блок datas ─────────────────────────
H1 "8. FitIntelDesktop.spec — блок datas (и полный файл)"
$specPath = Join-Path $desktop "FitIntelDesktop.spec"
if (Test-Path $specPath) {
    $content = Get-Content $specPath -Raw -Encoding UTF8
    W $content
    Write-Host "  ✓ FitIntelDesktop.spec — $((Get-Content $specPath).Count) строк" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $specPath"
}

# ─── 9. БОНУС: main_window.TAB_REGISTRY ──────────────────────────
H1 "9. БОНУС: main_window.py — TAB_REGISTRY + _make_widget (фрагмент)"
$mwPath = Join-Path $desktop "windows\main_window.py"
if (Test-Path $mwPath) {
    $mwLines = Get-Content $mwPath -Encoding UTF8
    $start = -1; $end = -1
    for ($i = 0; $i -lt $mwLines.Count; $i++) {
        if ($mwLines[$i] -match "^TAB_REGISTRY\s*=") { $start = $i; break }
    }
    if ($start -ge 0) {
        $end = [Math]::Min($start + 60, $mwLines.Count - 1)
        for ($i = $start; $i -lt $mwLines.Count; $i++) {
            if ($mwLines[$i] -match "^\}" -and $i -gt $start) { $end = $i; break }
        }
        W "  Строки $($start+1)..$($end+1):"
        W ""
        for ($i = $start; $i -le $end; $i++) { W "  $($mwLines[$i])" }
    }
    Write-Host "  ✓ main_window.py — TAB_REGISTRY" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $mwPath"
}

# ─── 10. БОНУС: help_dialog.py — список HELP_TEXTS ───────────────
H1 "10. БОНУС: help_dialog.py — ключи HELP_TEXTS"
$helpPath = Join-Path $desktop "windows\help_dialog.py"
if (Test-Path $helpPath) {
    $helpLines = Get-Content $helpPath -Encoding UTF8
    W "  Ключи HELP_TEXTS (для добавления новых записей):"
    W ""
    $inDict = $false
    foreach ($line in $helpLines) {
        if ($line -match "^HELP_TEXTS\s*=") { $inDict = $true; continue }
        if ($inDict -and $line -match "^\s*['""]([^'""]+)['""]:") {
            W "  - $($Matches[1])"
        }
        if ($inDict -and $line -match "^\}") { break }
    }
    Write-Host "  ✓ help_dialog.py — ключи собраны" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $helpPath"
}

# ─── 11. БОНУС: paths.py ─────────────────────────────────────────
H1 "11. БОНУС: paths.py — полностью"
$pathsFile = Join-Path $desktop "paths.py"
if (Test-Path $pathsFile) {
    W (Get-Content $pathsFile -Raw -Encoding UTF8)
    Write-Host "  ✓ paths.py" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $pathsFile"
}

# ─── 12. БОНУС: app_logging.py ───────────────────────────────────
H1 "12. БОНУС: app_logging.py — полностью"
$logFile = Join-Path $desktop "app_logging.py"
if (Test-Path $logFile) {
    W (Get-Content $logFile -Raw -Encoding UTF8)
    Write-Host "  ✓ app_logging.py" -ForegroundColor Cyan
} else {
    W "  ⚠ НЕ НАЙДЕН: $logFile"
}

# ─── запись файла ────────────────────────────────────────────────
$outPath = if ([System.IO.Path]::IsPathRooted($OutFile)) {
    $OutFile
} else {
    Join-Path (Get-Location).Path $OutFile
}
$script:lines -join "`r`n" | Set-Content -Path $outPath -Encoding UTF8

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  ✅ ГОТОВО" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
$size = (Get-Item $outPath).Length
$lineCount = (Get-Content $outPath).Count
Write-Host "  Файл:    $outPath"
Write-Host "  Размер:  $([math]::Round($size / 1024, 1)) КБ"
Write-Host "  Строк:   $lineCount"
Write-Host ""
Write-Host "  Что внутри:" -ForegroundColor Yellow
Write-Host "    1. api/client.py (полностью)"
Write-Host "    2. windows/users_tab.py (полностью)"
Write-Host "    3. windows/subscriptions_tab.py (полностью)"
Write-Host "    4. assets/ — список файлов + проверка TTF"
Write-Host "    5. windows/roles_tab.py (полностью)"
Write-Host "    6. permissions — из psql / docker / docs"
Write-Host "    7. windows/form_dialog.py (полностью)"
Write-Host "    8. FitIntelDesktop.spec (полностью)"
Write-Host "    9. БОНУС: TAB_REGISTRY из main_window.py"
Write-Host "   10. БОНУС: ключи HELP_TEXTS"
Write-Host "   11. БОНУС: paths.py"
Write-Host "   12. БОНУС: app_logging.py"
Write-Host ""
Write-Host "  Следующий шаг:" -ForegroundColor Yellow
Write-Host "    Откройте файл и пришлите его содержимое мне (или загрузите как файл)."
Write-Host "    После этого я соберу финальный промт v4."