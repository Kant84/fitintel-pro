# test_time_override_debug.ps1
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

# Используем существующего клиента a18228f4-5553-4b61-b048-e2f98119e1f5 с абонементом 1b89ff5b-c1b0-42f8-ad06-087bc13b343a
$clientId = "a18228f4-5553-4b61-b048-e2f98119e1f5"

Write-Host "Текущее время: $(Get-Date -Format 'HH:mm:ss')"
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
