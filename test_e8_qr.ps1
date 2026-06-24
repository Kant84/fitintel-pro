# test_e8_qr.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.14 Вход через QR-код (positive) ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    qr_payload = "qr_code_payload_12345"
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "OK: Вход через QR выполнен"
    Write-Host "  visit_id: $response.id"
    Write-Host "  client_id: $response.client_id"
    Write-Host "  status: $response.status"
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Error: $err"
}
