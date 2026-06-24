# test_e8_force_exit.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Принудительный выход ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Выходим из активного посещения
$body = @{
    visit_id = "4781928a-c81f-446c-bf93-67529a057745"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "OK: Выход выполнен"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}
