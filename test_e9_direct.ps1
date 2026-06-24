# test_e9_direct.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E9 — Прямой тест endpoint'ов ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# E9.1: Открытие по карте
Write-Host "
E9.1: /api/v1/access/open"
try {
    $body = @{ credential = "qr_code_payload_12345"; device_id = "turnstile_01"; zone = "GYM" } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: granted=$($r.granted)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.6: Статус устройств
Write-Host "
E9.6: /api/v1/access/status"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/status" -Method GET -Headers $headers
    Write-Host "  OK: total=$($r.total)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.13: Экстренное открытие
Write-Host "
E9.13: /api/v1/access/emergency-unlock"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/emergency-unlock" -Method POST -Headers $headers
    Write-Host "  OK: unlocked=$($r.unlocked_count)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

Write-Host "
=== Готово! ==="
