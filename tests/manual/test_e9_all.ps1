# test_e9_all.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E9 — Полный тест ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# E9.2: Заблокированная карта
Write-Host "
E9.2: Заблокированная карта (negative)"
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE credentials SET status = 'BLOCKED' WHERE credential_value = 'qr_code_payload_12345';" | Out-Null
$body = @{ credential = "qr_code_payload_12345"; device_id = "turnstile_01"; zone = "GYM" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($r.granted -eq $false) { Write-Host "  OK: Доступ запрещён — $($r.reason)" } else { Write-Host "  ERROR: Должен быть запрещён!" }
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE credentials SET status = 'ACTIVE' WHERE credential_value = 'qr_code_payload_12345';" | Out-Null

# E9.3: Неизвестная карта
Write-Host "
E9.3: Неизвестная карта (negative)"
$body = @{ credential = "UNKNOWN_CARD_99999"; device_id = "turnstile_01"; zone = "GYM" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($r.granted -eq $false) { Write-Host "  OK: Карта не найдена — $($r.reason)" } else { Write-Host "  ERROR: Должен быть запрещён!" }
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.4: Ручное открытие
Write-Host "
E9.4: Ручное открытие (positive)"
$body = @{ device_id = "turnstile_01"; reason = "Клиент забыл карту" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/manual-open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: success=$($r.success), device_id=$($r.device_id)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.7: Блокировка устройства
Write-Host "
E9.7: Блокировка устройства (positive)"
$body = @{ reason = "Техническое обслуживание" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/turnstile_01/block" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: blocked=$($r.blocked)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.8: Разблокировка устройства
Write-Host "
E9.8: Разблокировка устройства (positive)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/turnstile_01/unblock" -Method POST -Headers $headers
    Write-Host "  OK: blocked=$($r.blocked)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.9: Логи доступа
Write-Host "
E9.9: Логи доступа (positive)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/logs" -Method GET -Headers $headers
    Write-Host "  OK: total=$($r.total) записей"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E9.10: Anti-passback
Write-Host "
E9.10: Anti-passback (negative)"
# Включаем anti-passback на устройстве
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE devices SET anti_passback_enabled = true WHERE code = 'turnstile_01';" | Out-Null
# Входим
$body = @{ credential = "qr_code_payload_12345"; device_id = "turnstile_01"; zone = "GYM" } | ConvertTo-Json
$r1 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
# Пытаемся войти снова без выхода
$r2 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
if ($r2.granted -eq $false -and $r2.reason -like "*Anti-passback*") {
    Write-Host "  OK: Anti-passback работает — $($r2.reason)"
} else {
    Write-Host "  INFO: $($r2.granted) — $($r2.reason)"
}
# Выключаем anti-passback
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE devices SET anti_passback_enabled = false WHERE code = 'turnstile_01';" | Out-Null

# E9.11: График доступа — вне времени
Write-Host "
E9.11: График доступа — вне времени (negative)"
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE devices SET work_schedule = '{\"start\": \"08:00\", \"end\": \"22:00\"}' WHERE code = 'turnstile_01';" | Out-Null
$body = @{ credential = "qr_code_payload_12345"; device_id = "turnstile_01"; zone = "GYM" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($r.granted -eq $false -and $r.reason -like "*вне рабочего*") {
        Write-Host "  OK: Вне рабочего времени — $($r.reason)"
    } else {
        Write-Host "  INFO: granted=$($r.granted), reason=$($r.reason)"
    }
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }
# Убираем график
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE devices SET work_schedule = NULL WHERE code = 'turnstile_01';" | Out-Null

Write-Host "
=== Готово! ==="
