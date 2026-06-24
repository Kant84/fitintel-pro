# test_e8_13_face_confidence.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.13 Face ID низкая уверенность (negative) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Обновляем face_template_123 с face_confidence = 0.80 (80%)
Write-Host "Обновляем credential с face_confidence = 0.80..."
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE credentials SET face_confidence = 0.80 WHERE credential_value = 'face_template_123';"

# Тест 1: Вход с confidence = 0.90 (выше 0.80) — должен работать
Write-Host "
Тест 1: confidence = 0.90 (выше порога 0.80) — должен работать"
$body = @{
    face_id = "face_template_123"
    face_confidence = 0.90
    access_method = "FACE_ID"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $visitId = $response.id
    Write-Host "OK: Вход выполнен (confidence 0.90 > 0.80)"
    
    # Выходим
    $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
    Write-Host "Выход выполнен"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# Тест 2: Вход с confidence = 0.50 (ниже 0.80) — должен быть запрещён
Write-Host "
Тест 2: confidence = 0.50 (ниже порога 0.80) — должен быть запрещён"
$body = @{
    face_id = "face_template_123"
    face_confidence = 0.50
    access_method = "FACE_ID"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "ERROR: Вход должен быть запрещён!"
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Response: $err"
    if ($err -like "*уверенность*" -or $err -like "*confidence*") {
        Write-Host "OK: Вход запрещён (низкая уверенность)"
    } else {
        Write-Host "INFO: Ошибка: $err"
    }
}

Write-Host "
=== Готово! ==="
