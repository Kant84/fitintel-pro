param(
    [string]$OutFile = "_context_for_prompt.txt"
)
$ErrorActionPreference = "Continue"
$lines = New-Object System.Collections.Generic.List[string]
function W([string]$s = "") { $lines.Add($s) }
function H1([string]$s) {
    W ""; W ("=" * 78); W "  " + $s; W ("=" * 78); W ""
}

$root = "E:\FitNexus AI\FitIntel AI"
$desktop = Join-Path $root "fitintel-desktop"
if (-not (Test-Path $desktop)) {
    Write-Host "[ERROR] fitintel-desktop not found at $desktop" -ForegroundColor Red
    exit 1
}

function DumpFile([string]$path, [string]$title) {
    H1 $title
    if (Test-Path $path) {
        try {
            $c = Get-Content $path -Raw -Encoding UTF8
            if ($c) { W $c } else { W "  (empty file)" }
            $n = (Get-Content $path -Encoding UTF8).Count
            Write-Host "  [OK] $title - $n lines" -ForegroundColor Cyan
        } catch {
            W "  [ERROR] $($_.Exception.Message)"
            Write-Host "  [ERROR] $title : $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        W "  [WARN] NOT FOUND: $path"
        Write-Host "  [WARN] not found: $title" -ForegroundColor Yellow
    }
}

# 1. api/client.py
DumpFile (Join-Path $desktop "api\client.py") "1. api/client.py"

# 2. users_tab.py
DumpFile (Join-Path $desktop "windows\users_tab.py") "2. windows/users_tab.py"

# 3. subscriptions_tab.py
DumpFile (Join-Path $desktop "windows\subscriptions_tab.py") "3. windows/subscriptions_tab.py"

# 4. assets/
H1 "4. assets/ - file list"
$assetsDir = Join-Path $desktop "assets"
if (Test-Path $assetsDir) {
    $files = Get-ChildItem -Path $assetsDir -Recurse -File -ErrorAction SilentlyContinue
    W "  Total: $($files.Count)"
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($desktop.Length + 1)
        W ("  {0,10} bytes  {1}" -f $f.Length, $rel)
    }
    $ttf = Get-ChildItem -Path $assetsDir -Recurse -Include *.ttf,*.otf -ErrorAction SilentlyContinue
    if ($ttf) {
        W ""
        W "  [OK] FONTS:"
        foreach ($t in $ttf) { W "     - $($t.Name) ($($t.Length) bytes)" }
    } else {
        W "  [WARN] no TTF/OTF fonts (PDF Cyrillic will fail without DejaVuSans.ttf)"
    }
    Write-Host "  [OK] assets/ - $($files.Count) files" -ForegroundColor Cyan
} else {
    W "  [WARN] NOT FOUND: $assetsDir"
}

# 5. roles_tab.py
DumpFile (Join-Path $desktop "windows\roles_tab.py") "5. windows/roles_tab.py"

# 6. permissions
H1 "6. permissions"
$rbacDoc = Join-Path $root "docs\RBAC (2).md"
if (Test-Path $rbacDoc) {
    W "  Source: docs/RBAC (2).md"
    W ""
    $md = Get-Content $rbacDoc -Encoding UTF8 -TotalCount 600 -ErrorAction SilentlyContinue
    foreach ($line in $md) { W "  $line" }
    Write-Host "  [OK] RBAC (2).md - $($md.Count) lines" -ForegroundColor Cyan
} else {
    W "  [WARN] not found: docs/RBAC (2).md"
}

# 7. form_dialog.py
DumpFile (Join-Path $desktop "windows\form_dialog.py") "7. windows/form_dialog.py"

# 8. spec
DumpFile (Join-Path $desktop "FitIntelDesktop.spec") "8. FitIntelDesktop.spec"

# 9. TAB_REGISTRY
H1 "9. main_window.py - TAB_REGISTRY"
$mwPath = Join-Path $desktop "windows\main_window.py"
if (Test-Path $mwPath) {
    $mwLines = Get-Content $mwPath -Encoding UTF8
    $start = -1
    for ($i = 0; $i -lt $mwLines.Count; $i++) {
        if ($mwLines[$i] -match "^TAB_REGISTRY\s*=") { $start = $i; break }
    }
    if ($start -ge 0) {
        $end = $start
        for ($i = $start; $i -lt $mwLines.Count; $i++) {
            if ($mwLines[$i] -match "^\}") { $end = $i; break }
        }
        for ($i = $start; $i -le $end; $i++) { W "  $($mwLines[$i])" }
    } else {
        W "  [WARN] TAB_REGISTRY not found in main_window.py"
    }
    Write-Host "  [OK] TAB_REGISTRY" -ForegroundColor Cyan
} else {
    W "  [WARN] NOT FOUND: $mwPath"
}

# 10. HELP_TEXTS keys
H1 "10. help_dialog.py - HELP_TEXTS keys"
$helpPath = Join-Path $desktop "windows\help_dialog.py"
if (Test-Path $helpPath) {
    $helpLines = Get-Content $helpPath -Encoding UTF8
    $inDict = $false
    foreach ($line in $helpLines) {
        if ($line -match "^HELP_TEXTS\s*=") { $inDict = $true; continue }
        if ($inDict -and $line -match "^\s*['""]([^'""]+)['""]:") {
            W "  - $($Matches[1])"
        }
        if ($inDict -and $line -match "^\}") { break }
    }
    Write-Host "  [OK] HELP_TEXTS keys" -ForegroundColor Cyan
} else {
    W "  [WARN] NOT FOUND: $helpPath"
}

# 11. paths.py
DumpFile (Join-Path $desktop "paths.py") "11. paths.py"

# 12. app_logging.py
DumpFile (Join-Path $desktop "app_logging.py") "12. app_logging.py"

# write
$outPath = if ([System.IO.Path]::IsPathRooted($OutFile)) { $OutFile } else { Join-Path (Get-Location).Path $OutFile }
$utf8bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($outPath, ($lines -join "`r`n"), $utf8bom)

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  DONE" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  File:   $outPath"
Write-Host "  Size:   $([math]::Round((Get-Item $outPath).Length / 1024, 1)) KB"
Write-Host "  Lines:  $((Get-Content $outPath).Count)"
Write-Host ""
Write-Host "  Send this file back to me." -ForegroundColor Yellow