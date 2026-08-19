# test_e4_with_tariff_fixed.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.4 — Создание тарифа с лимитом 1 ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создаём тариф с лимитом 1
$tariffBody = @{
    code = "TEST_LIMIT_1_$(Get-Random)"
    name = "Test Limit 1"
    description = "Тариф для теста лимита"
    price = 1000
    currency = "RUB"
    duration_days = 30
    visit_limit = 1
    is_unlimited = $false
} | ConvertTo-Json

try {
    $newTariff = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($tariffBody))
    $tariffId = $newTariff.id
    Write-Host "Тариф создан: $tariffId"
    
    # Создаём клиента
    $newClientBody = @{
        first_name = "Limit"
        last_name = "Test"
        phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
        email = "limit$(Get-Random)@test.com"
        gender = "MALE"
        client_category = "ADULT"
    } | ConvertTo-Json
    
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
    $clientId = $newClient.id
    Write-Host "Клиент создан: $clientId"
    
    # Создаём абонемент
    $subBody = @{
        client_id = $clientId
        tariff_id = $tariffId
        start_date = "2026-06-01"
        end_date = "2026-08-01"
        price = 1000
        currency = "RUB"
    } | ConvertTo-Json
    
    $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
    $subId = $newSub.id
    Write-Host "Абонемент создан: $subId"
    
    # Проверяем в БД
    psql -h 127.0.0.1 -U postgres -d fitnexus -c "SELECT id, visit_limit, visits_used, is_unlimited FROM subscriptions WHERE id = '$subId';"
    
    # Входим (1/1)
    $body = @{
        client_id = $clientId
        access_method = "QR"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $visitId = $response.id
    Write-Host "Вход 1/1 выполнен: $visitId"
    
    # Выходим
    $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
    Write-Host "Выход выполнен"
    
    # Пытаемся войти снова (лимит исчерпан)
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "ERROR: Должна быть ошибка!"
    } catch {
        $err = $_.ErrorDetails.Message
        Write-Host "Response: $err"
        if ($err -like "*имит*" -or $err -like "*исчерпан*") {
            Write-Host "OK: Лимит посещений исчерпан (402)"
        } else {
            Write-Host "INFO: Ошибка: $err"
        }
    }
    
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
