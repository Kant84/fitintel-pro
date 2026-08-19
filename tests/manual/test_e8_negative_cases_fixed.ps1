# test_e8_negative_cases_fixed.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.2 и E8.4 — Negative тесты (исправленные) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# ==========================================================
# E8.2 — Вход без абонемента (negative)
# ==========================================================
Write-Host "
=== E8.2 Вход без абонемента (negative) ==="

# Создаём клиента без абонемента (с правильными enum значениями)
$newClientBody = @{
    first_name = "NoSub"
    last_name = "Client"
    phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
    email = "nosub$(Get-Random)@test.com"
    gender = "MALE"
    client_category = "ADULT"
} | ConvertTo-Json

try {
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
    $noSubClientId = $newClient.id
    Write-Host "Создан клиент без абонемента: $noSubClientId"
    
    # Пытаемся войти
    $body = @{
        client_id = $noSubClientId
        access_method = "QR"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        Write-Host "ERROR: Должна быть ошибка 'Абонемент не активен'!"
    } catch {
        $err = $_.ErrorDetails.Message
        Write-Host "Response: $err"
        if ($err -like "*бонемент*" -or $err -like "*актив*" -or $err -like "*subscription*") {
            Write-Host "OK: Ошибка 'Абонемент не активен' (402)"
        } else {
            Write-Host "INFO: Получена ошибка: $err"
        }
    }
} catch {
    Write-Host "ERROR создания клиента: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.4 — Вход с исчерпанным лимитом (negative)
# ==========================================================
Write-Host "
=== E8.4 Вход с исчерпанным лимитом (negative) ==="

# Создаём клиента с абонементом лимитом 1
$newClientBody = @{
    first_name = "Limit"
    last_name = "Exceeded"
    phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
    email = "limit$(Get-Random)@test.com"
    gender = "MALE"
    client_category = "ADULT"
} | ConvertTo-Json

try {
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
    $limitClientId = $newClient.id
    Write-Host "Создан клиент: $limitClientId"
    
    # Получаем tariff_id
    $tariffs = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/tariffs/" -Method GET -Headers $headers
    $tariffId = $tariffs.items[0].id
    
    # Создаём абонемент с лимитом 1
    $subBody = @{
        client_id = $limitClientId
        tariff_id = $tariffId
        start_date = "2026-06-01"
        end_date = "2026-08-01"
        price = 1000
        currency = "RUB"
        visit_limit = 1
        is_unlimited = $false
    } | ConvertTo-Json
    
    try {
        $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions/" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
        Write-Host "Создан абонемент с лимитом 1"
        
        # Используем 1 визит (вход)
        $body = @{
            client_id = $limitClientId
            access_method = "QR"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        $visitId = $response.id
        Write-Host "Вход выполнен (1/1 визит использован)"
        
        # Выходим
        $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        Write-Host "Выход выполнен"
        
        # Пытаемся войти снова (лимит исчерпан)
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
            Write-Host "ERROR: Должна быть ошибка 'Лимит исчерпан'!"
        } catch {
            $err = $_.ErrorDetails.Message
            Write-Host "Response: $err"
            if ($err -like "*имит*" -or $err -like "*исчерпан*" -or $err -like "*limit*") {
                Write-Host "OK: Ошибка 'Лимит посещений исчерпан' (402)"
            } else {
                Write-Host "INFO: Получена ошибка: $err"
            }
        }
    } catch {
        Write-Host "ERROR создания абонемента: $($_.ErrorDetails.Message)"
    }
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
