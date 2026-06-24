# test_e8_remaining.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8 — Оставшиеся тесты ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# ==========================================================
# E8.10 — Фильтрация по дате (positive)
# ==========================================================
Write-Host "
=== E8.10 Фильтрация по дате (positive) ==="
$today = Get-Date -Format "yyyy-MM-dd"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/?date_from=$today&date_to=$today" -Method GET -Headers $headers
    Write-Host "OK: Посещения за $today получены"
    Write-Host "  Всего: $($response.count)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.11 — Авто-закрытие посещения (positive)
# ==========================================================
Write-Host "
=== E8.11 Авто-закрытие посещения (positive) ==="
Write-Host "Создаём посещение без выхода..."

# Создаём посещение
$body = @{
    client_id = "33253d11-d5d0-4fca-9b80-e0b85367f43f"
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $autoVisitId = $response.id
    Write-Host "OK: Вход выполнен, visit_id: $autoVisitId"
    Write-Host "Для теста E8.11 нужно запустить cron-задачу или подождать 24ч"
    Write-Host "Пропускаем (требует ручного запуска cron)"
    
    # Выходим, чтобы не блокировать
    $exitBody = @{ visit_id = $autoVisitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# ==========================================================
# E8.13 — Face ID низкая уверенность (negative)
# ==========================================================
Write-Host "
=== E8.13 Face ID низкая уверенность (negative) ==="
Write-Host "Требует реализации confidence score в Face ID сервисе"
Write-Host "Пропускаем (требует доработки Face Recognition сервиса)"

# ==========================================================
# E8.2 — Вход без абонемента (negative)
# ==========================================================
Write-Host "
=== E8.2 Вход без абонемента (negative) ==="

# Создаём клиента без абонемента
$newClientBody = @{
    first_name = "NoSub"
    last_name = "Client"
    phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
    gender = "male"
    client_category = "standard"
} | ConvertTo-Json

try {
    $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
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
        if ($err -like "*бонемент*") {
            Write-Host "OK: Ошибка 'Абонемент не активен' (402)"
        } else {
            Write-Host "ERROR: Неожиданная ошибка: $err"
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

# Находим абонемент с visits_used = visit_limit
$subs = psql -h 127.0.0.1 -U postgres -d fitnexus -c "SELECT id, client_id, visit_limit, visits_used FROM subscriptions WHERE visit_limit IS NOT NULL AND visits_used >= visit_limit LIMIT 1;" 2>$null
if ($subs) {
    Write-Host "Найден абонемент с исчерпанным лимитом"
    # Тестируем вход
} else {
    Write-Host "SKIP: Нет абонемента с исчерпанным лимитом"
    Write-Host "Создаём тестовый абонемент с лимитом 1 и использованием 1..."
    
    # Создаём клиента
    $newClientBody = @{
        first_name = "Limit"
        last_name = "Exceeded"
        phone = "+7999$(Get-Random -Minimum 1000000 -Maximum 9999999)"
        gender = "male"
        client_category = "standard"
    } | ConvertTo-Json
    
    try {
        $newClient = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/clients" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($newClientBody))
        $limitClientId = $newClient.id
        
        # Создаём абонемент с лимитом 1
        $subBody = @{
            client_id = $limitClientId
            tariff_id = "11111111-1111-1111-1111-111111111111"
            start_date = "2026-06-01"
            end_date = "2026-08-01"
            price = 1000
            currency = "RUB"
            visit_limit = 1
            is_unlimited = $false
        } | ConvertTo-Json
        
        $newSub = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/subscriptions" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($subBody))
        $limitSubId = $newSub.id
        
        # Используем 1 визит
        $body = @{
            client_id = $limitClientId
            access_method = "QR"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        $visitId = $response.id
        
        # Выходим
        $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        
        # Пытаемся войти снова (лимит исчерпан)
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
            Write-Host "ERROR: Должна быть ошибка 'Лимит исчерпан'!"
        } catch {
            $err = $_.ErrorDetails.Message
            if ($err -like "*имит*" -or $err -like "*исчерпан*") {
                Write-Host "OK: Ошибка 'Лимит посещений исчерпан' (402)"
            } else {
                Write-Host "ERROR: Неожиданная ошибка: $err"
            }
        }
    } catch {
        Write-Host "ERROR: $($_.ErrorDetails.Message)"
    }
}

Write-Host "
=== Готово! ==="
