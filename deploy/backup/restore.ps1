# FitIntel Pro - restore (PostgreSQL), ТЗ §9
# Использование: .\restore.ps1 backup_20260821_030000.sql
param([Parameter(Mandatory=$true)][string]$File)
$path = Join-Path $PSScriptRoot "..\..\backups" $File
if (-not (Test-Path $path)) { Write-Host "Файл не найден: $path"; exit 1 }
$env:PGPASSWORD = $env:FITINTEL_DB_PASSWORD
& psql -h 127.0.0.1 -U postgres -d fitintel -f $path
if ($LASTEXITCODE -eq 0) { Write-Host "Restore OK: $File" } else { Write-Host "Restore FAILED"; exit 1 }
