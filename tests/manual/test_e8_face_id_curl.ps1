# test_e8_face_id_curl.ps1
Write-Host "=== Debug Face ID с curl ==="

$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

# Используем curl напрямую с правильным JSON
$jsonBody = '{"face_id":"face_template_123","access_method":"FACE_ID"}'

$response = curl -s -X POST "http://localhost:8001/api/v1/visits/check-in" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d "$jsonBody"
Write-Host "Response: $response"
