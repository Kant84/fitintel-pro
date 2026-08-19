# test_e8_face_id_debug.ps1
Write-Host "=== Debug Face ID ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    face_id = "face_template_123"
    access_method = "FACE_ID"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body $body
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Error: $err"
}
