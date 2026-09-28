# Установка локального агента считывателя как автозапуск на любом ПК клуба.
# Запуск:  powershell -ExecutionPolicy Bypass -File install_reader_agent.ps1 -RepoPath "C:\FitIntel"
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [int]$Port = 8001
)
$ErrorActionPreference = "Stop"
$Py = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { Write-Error "Не найден python: $Py" }

$action  = New-ScheduledTaskAction -Execute $Py `
           -Argument "-m uvicorn app.main:app --host 127.0.0.1 --port $Port" `
           -WorkingDirectory $RepoPath
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit (New-TimeSpan -Hours 0)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" `
             -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "FitIntelReaderAgent" `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Force -Description "Локальный агент считывателя RFID (FitIntel)"

Write-Host "OK: агент зарегистрирован. Проверка: http://127.0.0.1:$Port/api/v1/reader/status"