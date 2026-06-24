# test_time_override_debug2.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Тест переопределения времени (с debug) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$clientId = "a18228f4-5553-4b61-b048-e2f98119e1f5"

# Сначала выходим (если есть активное посещение)
Write-Host "Проверяем активные посещения..."
try {
    $visits = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/client/$clientId" -Method GET -Headers $headers
    $activeVisit = $visits.items | Where-Object { $_.status -eq 'ACTIVE' } | Select-Object -First 1
    
    if ($activeVisit) {
        Write-Host "Найдено активное посещение: $($activeVisit.id). Выходим..."
        $exitBody = @{ visit_id = $activeVisit.id } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        Write-Host "Выход выполнен"
    }
} catch {
    Write-Host "Нет активных посещений или ошибка"
}

Write-Host "
Текущее время: $(Get-Date -Format 'HH:mm:ss')"
Write-Host "Время ВНЕ диапазона 10:00-18:00 — вход должен быть запрещён"

# Пытаемся войти
$body = @{
    client_id = $clientId
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "ERROR: Вход выполнен, но должен быть запрещён!"
    Write-Host "visit_id: $($response.id)"
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Response: $err"
    if ($err -like "*оступ*" -or $err -like "*запрещ*") {
        Write-Host "OK: Вход запрещён"
    } else {
        Write-Host "INFO: Ошибка: $err"
    }
}

Write-Host "
=== Готово! ==="
