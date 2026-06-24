# test_e9_access_control.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E9 — Access Control — Тесты ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# ==========================================================
# E9.1: Открытие по карте (positive)
# ==========================================================
Write-Host "
=== E9.1 Открытие по карте (positive) ==="
$body = @{
    credential = "qr_code_payload_12345"
    device_id = "turnstile_01"
    zone = "GYM"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "OK: Доступ $($response.granted)"
    Write-Host "  turnstile_open: $($response.turnstile_open)"
    Write-Host "  visit_id: $($response.visit_id)"
    
    # Выходим
    if ($response.visit_id) {
        $exitBody = @{ visit_id = $response.visit_id } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
    }
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E9.2: Заблокированная карта (negative)
# ==========================================================
Write-Host "
=== E9.2 Заблокированная карта (negative) ==="
# Блокируем credential
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE credentials SET status = 'BLOCKED' WHERE credential_value = 'qr_code_payload_12345';"

$body = @{
    credential = "qr_code_payload_12345"
    device_id = "turnstile_01"
    zone = "GYM"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($response.granted -eq $false) {
        Write-Host "OK: Доступ запрещён — $($response.reason)"
    } else {
        Write-Host "ERROR: Доступ должен быть запрещён!"
    }
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# Разблокируем обратно
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE credentials SET status = 'ACTIVE' WHERE credential_value = 'qr_code_payload_12345';"

# ==========================================================
# E9.3: Неизвестная карта (negative)
# ==========================================================
Write-Host "
=== E9.3 Неизвестная карта (negative) ==="
$body = @{
    credential = "UNKNOWN_CARD_99999"
    device_id = "turnstile_01"
    zone = "GYM"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($response.granted -eq $false) {
        Write-Host "OK: Карта не найдена — $($response.reason)"
    } else {
        Write-Host "ERROR: Доступ должен быть запрещён!"
    }
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E9.6: Статус устройств
# ==========================================================
Write-Host "
=== E9.6 Статус устройств (positive) ==="
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/status" -Method GET -Headers $headers
    Write-Host "OK: Статус получен"
    Write-Host "  Всего: $($response.total)"
    Write-Host "  Онлайн: $($response.online)"
    Write-Host "  Офлайн: $($response.offline)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E9.13: Экстренное открытие
# ==========================================================
Write-Host "
=== E9.13 Экстренное открытие (positive) ==="
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/emergency-unlock" -Method POST -Headers $headers
    Write-Host "OK: Экстренное открытие выполнено"
    Write-Host "  Открыто устройств: $($response.unlocked_count)"
    Write-Host "  Сообщение: $($response.message)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
