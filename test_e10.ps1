# test_e10.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E10 — Credentials — Тесты ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# E10.1: Создание карты
Write-Host "
E10.1: Создание карты (positive)"
$body = @{
    client_id = "33253d11-d5d0-4fca-9b80-e0b85367f43f"
    card_number = "TEST_CARD_12345"
    valid_until = "2026-12-31"
} | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/card" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $cardId = $r.id
    Write-Host "  OK: card_id=$($cardId)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.2: Дублирующая карта
Write-Host "
E10.2: Дублирующая карта (negative)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/card" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  ERROR: Должен быть 409!"
} catch {
    if ($_.ErrorDetails.Message -like "*409*" -or $_.ErrorDetails.Message -like "*существует*") {
        Write-Host "  OK: Карта уже существует"
    } else {
        Write-Host "  ERROR: $($_.ErrorDetails.Message)"
    }
}

# E10.3: Создание браслета
Write-Host "
E10.3: Создание браслета (positive)"
$body = @{
    client_id = "33253d11-d5d0-4fca-9b80-e0b85367f43f"
    bracelet_id = "BRACELET_001"
    rfid_manufacturer = "Kerong"
    rfid_model = "KR-S50"
} | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/bracelet" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $braceletId = $r.id
    Write-Host "  OK: bracelet_id=$($braceletId)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.4: Создание мобильного ключа
Write-Host "
E10.4: Создание мобильного ключа (positive)"
$body = @{
    client_id = "33253d11-d5d0-4fca-9b80-e0b85367f43f"
    device_id = "IPHONE_12_ABC123"
    device_name = "iPhone 12 Андрея"
} | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/mobile-key" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $mobileKeyId = $r.id
    Write-Host "  OK: mobile_key_id=$($mobileKeyId)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.5: Список credentials клиента
Write-Host "
E10.5: Список credentials клиента (positive)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/client/33253d11-d5d0-4fca-9b80-e0b85367f43f" -Method GET -Headers $headers
    Write-Host "  OK: count=$($r.count)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.6: Блокировка карты
Write-Host "
E10.6: Блокировка карты (positive)"
$body = @{ reason = "Потеряна" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/block" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: status=$($r.status)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.7: Разблокировка карты
Write-Host "
E10.7: Разблокировка карты (positive)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/unblock" -Method POST -Headers $headers
    Write-Host "  OK: status=$($r.status)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.11: Валидация карты
Write-Host "
E10.11: Валидация карты (positive)"
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/validate" -Method GET -Headers $headers
    Write-Host "  OK: valid=$($r.valid), subscription_active=$($r.subscription_active)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.12: Валидация заблокированной карты
Write-Host "
E10.12: Валидация заблокированной карты (negative)"
# Блокируем снова
$body = @{ reason = "Тест" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/block" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) | Out-Null
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/validate" -Method GET -Headers $headers
    Write-Host "  OK: valid=$($r.valid), reason=$($r.reason)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.13: Эмуляция кард-ридера
Write-Host "
E10.13: Эмуляция кард-ридера (positive)"
$body = @{ card_data = ";1234567890=1234?"; format = "magstripe" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/emulate" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: success=$($r.success), card_number=$($r.card_number)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.14: Эмуляция — неподдерживаемый формат
Write-Host "
E10.14: Эмуляция — неподдерживаемый формат (negative)"
$body = @{ card_data = "%%%%%"; format = "auto" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/emulate" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    if ($r.success -eq $false) {
        Write-Host "  OK: reason=$($r.reason)"
    } else {
        Write-Host "  ERROR: Должен быть запрещён!"
    }
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.15: Программирование MIFARE
Write-Host "
E10.15: Программирование MIFARE (positive)"
$body = @{
    sector = 1
    key_a = "FFFFFFFFFFFF"
    data = "1234567890ABCDEF1234567890ABCDEF"
} | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId/program" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "  OK: success=$($r.success), sector=$($r.sector)"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

# E10.8: Удаление карты
Write-Host "
E10.8: Удаление карты (positive)"
try {
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/credentials/$cardId" -Method DELETE -Headers $headers
    Write-Host "  OK: Карта удалена"
} catch { Write-Host "  ERROR: $($_.ErrorDetails.Message)" }

Write-Host "
=== Готово! ==="
