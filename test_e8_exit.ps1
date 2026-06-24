# test_e8_exit.ps1
Write-Host "=== Тест E8.5: Выход клиента (exit) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Выход
$exitBody = @{
    visit_id = "f3c8ad7c-b782-4709-aefa-11708b34ec84"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/exit" -Method POST -Headers $headers -Body $exitBody
    Write-Host "OK: Выход выполнен"
    Write-Host "Visit ID: $($response.id)"
    Write-Host "Exit time: $($response.exit_time)"
    Write-Host "Duration: $($response.duration_minutes) минут"
    Write-Host "Status: $($response.status)"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}
