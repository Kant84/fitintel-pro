# FitIntel Pro - backup (PostgreSQL), ТЗ §9
# Планировщик: ежедневно 03:00, хранение 14 дней
$env:PGPASSWORD = $env:FITINTEL_DB_PASSWORD
$dir = Join-Path $PSScriptRoot "..\..\backups"
New-Item -ItemType Directory -Force $dir | Out-Null
$file = Join-Path $dir ("backup_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".sql")
& pg_dump -h 127.0.0.1 -U postgres -d fitintel -f $file
if ($LASTEXITCODE -eq 0) { Write-Host "Backup OK: $file" } else { Write-Host "Backup FAILED"; exit 1 }
# ротация: удалить старше 14 дней
Get-ChildItem $dir -Filter *.sql | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -Force
