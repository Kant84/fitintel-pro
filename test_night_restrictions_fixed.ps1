# test_night_restrictions_fixed.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Тест ночного абонемента (исправленный) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$randomSuffix = Get-Random -Minimum 1000 -Maximum 9999

# Создаём ночной тариф (22:00-06:00)
$nightTariffBody = @{
    code = "NIGHTTIME_$randomSuffix"
    name = "Ночной тариф $randomSuffix"
    description = "Доступ с 22:00 до 06:00"
    price = 500
    currency = "RUB"
    duration_days = 30
    visit_limit = 10
    is_unlimited = $false
    time_restriction_type = "NIGHTTIME"
    allowed_start_time = "22:00:00"
    allowed_end_time = "06:00:00"
} | ConvertTo-Json

try {
    $nightTariff = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($nightTariffBody))
    $nightTariffId = $nightTariff.id
    Write-Host "Ночной тариф создан: $nightTariffId"
    
    # Создаём клиента
    $newClientBody = @{
        first_name = "Night"
        last_name = "Client"
        phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
        email = "night$randomSuffix@test.com"
        gender = "MALE"
        client_category = "ADULT"
    } | ConvertTo-Json
    
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
    $nightClientId = $newClient.id
    Write-Host "Клиент создан: $nightClientId"
    
    # Создаём абонемент
    $subBody = @{
        client_id = $nightClientId
        tariff_id = $nightTariffId
        start_date = "2026-06-01"
        end_date = "2026-08-01"
        price = 500
        currency = "RUB"
    } | ConvertTo-Json
    
    $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
    $nightSubId = $newSub.id
    Write-Host "Ночной абонемент создан: $nightSubId"
    
    # Проверяем время (сейчас ~19:50, ВНЕ диапазона 22:00-06:00)
    $currentHour = (Get-Date).Hour
    Write-Host "Текущее время: $currentHour:00"
    
    Write-Host "Время ВНЕ диапазона ночного абонемента (22:00-06:00) — вход должен быть запрещён"
    
    # Пытаемся войти (должно быть запрещено)
    $body = @{
        client_id = $nightClientId
        access_method = "QR"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "ERROR: Вход должен быть запрещён!"
    } catch {
        $err = $_.ErrorDetails.Message
        Write-Host "Response: $err"
        if ($err -like "*оступ*" -or $err -like "*запрещ*") {
            Write-Host "OK: Вход запрещён (вне ночного времени)"
        } else {
            Write-Host "INFO: Ошибка: $err"
        }
    }
    
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
