# test_full_time_override.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Полный тест переопределения времени ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$clientId = "a18228f4-5553-4b61-b048-e2f98119e1f5"

# Сначала выходим (если есть активное посещение)
Write-Host "1. Выходим из активного посещения..."
try {
    $visits = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/client/$clientId" -Method GET -Headers $headers
    $activeVisit = $visits.items | Where-Object { $_.status -eq 'ACTIVE' } | Select-Object -First 1
    
    if ($activeVisit) {
        $exitBody = @{ visit_id = $activeVisit.id } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        Write-Host "   Выход выполнен"
    }
} catch {
    Write-Host "   Нет активных посещений"
}

# Тест 1: Вход ВНЕ времени (20:20, абонемент 10:00-18:00) — должен быть запрещён
Write-Host "
2. Тест входа ВНЕ времени (20:20, абонемент 10:00-18:00)..."
$body = @{
    client_id = $clientId
    access_method = "QR"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "   ERROR: Вход выполнен, но должен быть запрещён!"
} catch {
    $err = $_.ErrorDetails.Message
    if ($err -like "*запрещ*") {
        Write-Host "   OK: Вход запрещён (вне времени 10:00-18:00)"
    } else {
        Write-Host "   INFO: Ошибка: $err"
    }
}

# Тест 2: Вход ВНУТРИ времени (12:00, абонемент 10:00-18:00) — должен работать
Write-Host "
3. Тест входа ВНУТРИ времени (12:00, абонемент 10:00-18:00)..."
$body = @{
    client_id = $clientId
    access_method = "QR"
    entry_time = "2026-06-19T12:00:00"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    $visitId = $response.id
    Write-Host "   OK: Вход выполнен (время 12:00 в диапазоне 10:00-18:00)"
    
    # Выходим
    $exitBody = @{ visit_id = $visitId } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
    Write-Host "   Выход выполнен"
} catch {
    Write-Host "   ERROR: $($_.ErrorDetails.Message)"
}

# Тест 3: Вход на границе (09:59, абонемент 10:00-18:00) — должен быть запрещён
Write-Host "
4. Тест входа на границе (09:59, абонемент 10:00-18:00)..."
$body = @{
    client_id = $clientId
    access_method = "QR"
    entry_time = "2026-06-19T09:59:00"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "   ERROR: Вход выполнен, но должен быть запрещён!"
} catch {
    $err = $_.ErrorDetails.Message
    if ($err -like "*запрещ*") {
        Write-Host "   OK: Вход запрещён (09:59 < 10:00)"
    } else {
        Write-Host "   INFO: Ошибка: $err"
    }
}

# Тест 4: Вход на границе (18:01, абонемент 10:00-18:00) — должен быть запрещён
Write-Host "
5. Тест входа на границе (18:01, абонемент 10:00-18:00)..."
$body = @{
    client_id = $clientId
    access_method = "QR"
    entry_time = "2026-06-19T18:01:00"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "   ERROR: Вход выполнен, но должен быть запрещён!"
} catch {
    $err = $_.ErrorDetails.Message
    if ($err -like "*запрещ*") {
        Write-Host "   OK: Вход запрещён (18:01 > 18:00)"
    } else {
        Write-Host "   INFO: Ошибка: $err"
    }
}

Write-Host "
=== Готово! ==="
