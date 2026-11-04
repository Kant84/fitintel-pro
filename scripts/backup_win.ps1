# FitIntel Pro - ежедневный бэкап (облегченный: без пересоздаваемых каталогов)
$ErrorActionPreference = "Stop"
$src = "E:\FitNexus AI\FitIntel AI"
$dst = "E:\FitIntel-Backups"
$keep = 7
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $dst "fitintel_win_$stamp.zip"

# Исключаем ТОЛЬКО пересоздаваемое (восстанавливается из кода/зависимостей):
$excludeDirs = @(".venv","venv","dist","build","node_modules","__pycache__",
                 ".pytest_cache",".mypy_cache",".ruff_cache",".next","installer_out","logs")

New-Item -ItemType Directory -Force $dst | Out-Null

# Диагностика: топ-10 крупнейших каталогов (видно, что съело место)
Get-ChildItem $src -Directory | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
          Measure-Object Length -Sum).Sum
    [PSCustomObject]@{ Dir = $_.Name; MB = [math]::Round($s/1MB,1) }
} | Sort-Object MB -Descending | Select-Object -First 10 | Format-Table -AutoSize

$sevenZip = @("$env:ProgramFiles\7-Zip\7z.exe",
              "${env:ProgramFiles(x86)}\7-Zip\7z.exe") |
            Where-Object { Test-Path $_ } | Select-Object -First 1

if ($sevenZip) {
    $x = $excludeDirs | ForEach-Object { "-xr!$_" }
    & $sevenZip a -tzip -mx=5 $out $src @x | Select-Object -Last 2
} else {
    # Fallback: robocopy во временный каталог + Compress-Archive
    $stage = Join-Path $env:TEMP "fitintel_backup_stage"
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
    $xd = $excludeDirs | ForEach-Object { Join-Path $src $_ }
    robocopy $src $stage /E /XD $xd /NFL /NDL /NJH /NJS /NP | Out-Null
    Compress-Archive -Path "$stage\*" -DestinationPath $out -CompressionLevel Optimal
    Remove-Item $stage -Recurse -Force
}

if (-not (Test-Path $out)) { throw "Архив не создан" }
$mb = [math]::Round((Get-Item $out).Length/1MB,1)

# Ротация: оставляем последние $keep архивов
Get-ChildItem $dst -Filter "fitintel_win_*.zip" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip $keep |
  ForEach-Object { Remove-Item $_.FullName -Force }

Write-Host ("WIN_BACKUP_OK={0} ({1} MB)" -f $out, $mb)

