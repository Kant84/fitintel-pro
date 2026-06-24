# test_e8_face_id_utf8.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Debug Face ID с UTF-8 ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

# Формируем JSON вручную
$body = @{
    face_id = "face_template_123"
    access_method = "FACE_ID"
} | ConvertTo-Json

Write-Host "Отправляем: $body"

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    } -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "OK: $response"
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Error: $err"
}
