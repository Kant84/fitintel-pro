# test_e8_all_final.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8 — Visits (Посещения) — Полный тест ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$clientId = "33253d11-d5d0-4fca-9b80-e0b85367f43f"

# ==========================================================
# E8.1 — Регистрация входа (positive)
# ==========================================================
Write-Host "
=== E8.1 Регистрация входа (positive) ==="
$body = @{
    client_id = $clientId
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $visitId = $response.id
    Write-Host "OK: Вход выполнен"
    Write-Host "  visit_id: $visitId"
    Write-Host "  status: $response.status"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
    $visitId = $null
}

# ==========================================================
# E8.5 — Регистрация выхода (positive)
# ==========================================================
if ($visitId) {
    Write-Host "
=== E8.5 Регистрация выхода (positive) ==="
    $body = @{
        visit_id = $visitId
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "OK: Выход выполнен"
        Write-Host "  status: $response.status"
        Write-Host "  duration: $response.duration_minutes мин"
    } catch {
        Write-Host "ERROR: $($_.ErrorDetails.Message)"
    }
}

# ==========================================================
# E8.6 — Выход без входа (negative)
# ==========================================================
Write-Host "
=== E8.6 Выход без входа (negative) ==="
$fakeVisitId = "00000000-0000-0000-0000-000000000000"
$body = @{
    visit_id = $fakeVisitId
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "ERROR: Должна быть ошибка!"
} catch {
    Write-Host "OK: Ошибка (ожидаемо)"
    Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)"
}

# ==========================================================
# E8.7 — Список посещений (positive)
# ==========================================================
Write-Host "
=== E8.7 Список посещений (positive) ==="
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits?date_from=2026-06-01&date_to=2026-06-30" -Method GET -Headers $headers
    Write-Host "OK: Список получен"
    Write-Host "  Всего: $($response.total)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.8 — Посещение по ID (positive)
# ==========================================================
Write-Host "
=== E8.8 Посещение по ID (positive) ==="
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/$visitId" -Method GET -Headers $headers
    Write-Host "OK: Посещение найдено"
    Write-Host "  ID: $response.id"
    Write-Host "  Status: $response.status"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.9 — Фильтрация по клиенту (positive)
# ==========================================================
Write-Host "
=== E8.9 Фильтрация по клиенту (positive) ==="
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/client/$clientId" -Method GET -Headers $headers
    Write-Host "OK: Посещения клиента получены"
    Write-Host "  Всего: $($response.total)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.12 — Вход через Face ID (positive)
# ==========================================================
Write-Host "
=== E8.12 Вход через Face ID (positive) ==="
$body = @{
    face_id = "face_template_123"
    access_method = "FACE_ID"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $faceVisitId = $response.id
    Write-Host "OK: Вход через Face ID выполнен"
    Write-Host "  visit_id: $faceVisitId"
    
    # Выходим, чтобы не блокировать
    $exitBody = @{ visit_id = $faceVisitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.14 — Вход через QR-код (positive)
# ==========================================================
Write-Host "
=== E8.14 Вход через QR-код (positive) ==="
$body = @{
    qr_payload = "qr_code_payload_12345"
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $qrVisitId = $response.id
    Write-Host "OK: Вход через QR выполнен"
    Write-Host "  visit_id: $qrVisitId"
    
    # Выходим, чтобы не блокировать
    $exitBody = @{ visit_id = $qrVisitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
