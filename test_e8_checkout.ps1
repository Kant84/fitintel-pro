# test_e8_checkout.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.5: Выход клиента (check-out) ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Получаем активное посещение клиента
$visits = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/client/33253d11-d5d0-4fca-9b80-e0b85367f43f" -Method GET -Headers $headers
$activeVisit = $visits.items | Where-Object { $_.status -eq 'ACTIVE' } | Select-Object -First 1

if ($activeVisit) {
    Write-Host "Найдено активное посещение: $($activeVisit.id)"
    
    $body = @{
        visit_id = $activeVisit.id
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "OK: Выход выполнен"
        Write-Host "  visit_id: $response.id"
        Write-Host "  exit_time: $response.exit_time"
        Write-Host "  duration: $response.duration_minutes мин"
        Write-Host "  status: $response.status"
    } catch {
        $err = $_.ErrorDetails.Message
        Write-Host "Error: $err"
    }
} else {
    Write-Host "Активное посещение не найдено"
}
