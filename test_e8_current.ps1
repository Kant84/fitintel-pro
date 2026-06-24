# test_e8_current.ps1
Write-Host "=== Тест текущего visits endpoint ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Получаем список клиентов
Write-Host "
=== Получаем список клиентов ==="
$clients = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients" -Method GET -Headers $headers
Write-Host "Клиентов найдено: $($clients.items.Count)"

# Тестируем вход (entry)
Write-Host "
=== Тест E8.1: Вход клиента (entry) ==="
$clientId = "33253d11-d5d0-4fca-9b80-e0b85367f43f"  # клиент с активным абонементом
$entryBody = @{
    client_id = $clientId
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/entry" -Method POST -Headers $headers -Body $entryBody
    Write-Host "OK: Вход выполнен"
    Write-Host "Visit ID: $($response.id)"
    Write-Host "Entry time: $($response.entry_time)"
    Write-Host "Status: $($response.status)"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}
