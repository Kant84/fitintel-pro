# test_time_override.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Тест переопределения времени в абонементе ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создаём тариф FULLDAY (без ограничений)
$tariffBody = @{
    code = "FULLDAY_$(Get-Random)"
    name = "Полный день тариф"
    description = "Без ограничений по времени"
    price = 2000
    currency = "RUB"
    duration_days = 30
    visit_limit = 30
    is_unlimited = $false
    time_restriction_type = "FULLDAY"
} | ConvertTo-Json

$tariff = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($tariffBody))
$tariffId = $tariff.id
Write-Host "Тариф FULLDAY создан: $tariffId"

# Создаём клиента
$newClientBody = @{
    first_name = "Custom"
    last_name = "Time"
    phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
    email = "custom$(Get-Random)@test.com"
    gender = "MALE"
    client_category = "ADULT"
} | ConvertTo-Json

$newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
$clientId = $newClient.id
Write-Host "Клиент создан: $clientId"

# Создаём абонемент с переопределением времени: 10:00-18:00
$subBody = @{
    client_id = $clientId
    tariff_id = $tariffId
    start_date = "2026-06-01"
    end_date = "2026-08-01"
    price = 2000
    currency = "RUB"
    time_restriction_type = "DAYTIME"
    allowed_start_time = "10:00:00"
    allowed_end_time = "18:00:00"
} | ConvertTo-Json -Depth 10

Write-Host "
Создаём абонемент с переопределением времени 10:00-18:00..."
$newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
$subId = $newSub.id
Write-Host "Абонемент создан: $subId"

# Проверяем в БД
Write-Host "
Проверяем в БД:"
psql -h 127.0.0.1 -U postgres -d fitnexus -c "SELECT id, time_restriction_type, allowed_start_time, allowed_end_time FROM subscriptions WHERE id = '$subId';"

# Текущее время (должно быть ~20:00, ВНЕ 10:00-18:00)
$currentHour = (Get-Date).Hour
Write-Host "
Текущее время: $currentHour:00"
Write-Host "Время ВНЕ диапазона 10:00-18:00 — вход должен быть запрещён"

# Пытаемся войти
$body = @{
    client_id = $clientId
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "ERROR: Вход должен быть запрещён!"
} catch {
    $err = $_.ErrorDetails.Message
    Write-Host "Response: $err"
    if ($err -like "*оступ*" -or $err -like "*запрещ*") {
        Write-Host "OK: Вход запрещён (вне времени 10:00-18:00)"
    } else {
        Write-Host "INFO: Ошибка: $err"
    }
}

Write-Host "
=== Готово! ==="
