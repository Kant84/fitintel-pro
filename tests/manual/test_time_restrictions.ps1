# test_time_restrictions.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Тест временных абонементов ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создаём дневной тариф (06:00-22:00)
$dayTariffBody = @{
    code = "DAYTIME_$(Get-Random)"
    name = "Дневной тариф"
    description = "Доступ с 06:00 до 22:00"
    price = 1000
    currency = "RUB"
    duration_days = 30
    visit_limit = 10
    is_unlimited = $false
    time_restriction_type = "DAYTIME"
    allowed_start_time = "06:00:00"
    allowed_end_time = "22:00:00"
} | ConvertTo-Json

try {
    $dayTariff = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($dayTariffBody))
    $dayTariffId = $dayTariff.id
    Write-Host "Дневной тариф создан: $dayTariffId"
    
    # Создаём клиента
    $newClientBody = @{
        first_name = "Day"
        last_name = "Client"
        phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
        email = "day$(Get-Random)@test.com"
        gender = "MALE"
        client_category = "ADULT"
    } | ConvertTo-Json
    
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
    $dayClientId = $newClient.id
    Write-Host "Клиент создан: $dayClientId"
    
    # Создаём абонемент
    $subBody = @{
        client_id = $dayClientId
        tariff_id = $dayTariffId
        start_date = "2026-06-01"
        end_date = "2026-08-01"
        price = 1000
        currency = "RUB"
    } | ConvertTo-Json
    
    $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
    $daySubId = $newSub.id
    Write-Host "Дневной абонемент создан: $daySubId"
    
    # Проверяем время (сейчас ~19:36, должно быть в диапазоне 06:00-22:00)
    $currentHour = (Get-Date).Hour
    Write-Host "Текущее время: $currentHour:00"
    
    if ($currentHour -ge 6 -and $currentHour -lt 22) {
        Write-Host "Время в диапазоне дневного абонемента — вход должен работать"
        
        # Пытаемся войти
        $body = @{
            client_id = $dayClientId
            access_method = "QR"
        } | ConvertTo-Json
        
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
            $visitId = $response.id
            Write-Host "OK: Вход выполнен (дневное время): $visitId"
            
            # Выходим
            $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
            Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        } catch {
            Write-Host "ERROR: $($_.ErrorDetails.Message)"
        }
    } else {
        Write-Host "Время ВНЕ диапазона дневного абонемента — вход должен быть запрещён"
        
        # Пытаемся войти
        $body = @{
            client_id = $dayClientId
            access_method = "QR"
        } | ConvertTo-Json
        
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
            Write-Host "ERROR: Вход должен быть запрещён!"
        } catch {
            Write-Host "OK: Вход запрещён (вне дневного времени)"
        }
    }
    
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
