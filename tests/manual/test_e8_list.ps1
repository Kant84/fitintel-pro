# test_e8_list.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.7 Список посещений (positive) ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Тестируем с / в конце
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/" -Method GET -Headers $headers
    Write-Host "OK (с /): Список получен"
    Write-Host "  Всего: $($response.count)"
} catch {
    Write-Host "ERROR (с /): $($_.ErrorDetails.Message)"
}

# Тестируем без /
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits" -Method GET -Headers $headers
    Write-Host "OK (без /): Список получен"
    Write-Host "  Всего: $($response.count)"
} catch {
    Write-Host "ERROR (без /): $($_.ErrorDetails.Message)"
}
