# FitIntel: локальный бэкап репо + дистрибутива на Windows (ротация 14).
$ErrorActionPreference = 'Stop'
$Dst = 'E:\FitIntel-Backups'
$Ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
New-Item -ItemType Directory -Force $Dst | Out-Null
$Stage = Join-Path $Dst "_stage_$Ts"
robocopy 'E:\FitNexus AI\FitIntel AI' "$Stage\repo" /E /XD build dist .venv /NFL /NDL /NJH /NJS | Out-Null
if (Test-Path 'E:\FitIntel-Distribution') {
  robocopy 'E:\FitIntel-Distribution' "$Stage\distribution" /E /NFL /NDL /NJH /NJS | Out-Null
}
$Zip = Join-Path $Dst "fitintel_win_$Ts.zip"
Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $Zip -CompressionLevel Optimal -Force
Remove-Item $Stage -Recurse -Force
Get-ChildItem $Dst -Filter *.zip | Sort-Object LastWriteTime -Descending | Select-Object -Skip 14 | Remove-Item -Force
Write-Host "WIN_BACKUP_OK=$Zip"
