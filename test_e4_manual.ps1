# test_e4_manual.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.4 — Ручное создание абонемента с лимитом ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

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

# Получаем tariff_id
$tariffs = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method GET -Headers $headers
$tariffId = $tariffs.items[0].id
Write-Host "Tariff ID: $tariffId"

# Создаём абонемент с visit_limit=1
$subBody = @{
    client_id = $clientId
    tariff_id = $tariffId
    start_date = "2026-06-01"
    end_date = "2026-08-01"
    price = 1000
    currency = "RUB"
    visit_limit = 1
    is_unlimited = $false
} | ConvertTo-Json -Depth 10

Write-Host "Отправляем: $subBody"

try {
    $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
    Write-Host "Абонемент создан: $newSub"
    
    # Проверяем в БД
    $subId = $newSub.id
    psql -h 127.0.0.1 -U postgres -d fitnexus -c "SELECT id, client_id, visit_limit, visits_used, is_unlimited, is_active, status FROM subscriptions WHERE id = '$subId';"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}
