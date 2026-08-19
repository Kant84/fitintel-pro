# test_e8_11_auto_close.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E8.11 Авто-закрытие посещений (positive) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создаём посещение без выхода (вручную в БД, чтобы оно было "старым")
Write-Host "Создаём тестовое посещение без выхода (2 дня назад)..."

# Создаём через API, но потом изменим entry_time в БД
$body = @{
    client_id = "33253d11-d5d0-4fca-9b80-e0b85367f43f"
    access_method = "QR"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-in" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
$visitId = $response.id
Write-Host "Создано посещение: $visitId"

# Изменяем entry_time на 2 дня назад (через SQL)
psql -h 127.0.0.1 -U postgres -d fitnexus -c "UPDATE visits SET entry_time = NOW() - INTERVAL '2 days' WHERE id = '$visitId';"

# Запускаем авто-закрытие
Write-Host "
Запускаем авто-закрытие..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/auto-close?days_threshold=1" -Method POST -Headers $headers
    Write-Host "OK: Авто-закрытие выполнено"
    Write-Host "  Закрыто посещений: $($response.closed_count)"
    Write-Host "  Сообщение: $($response.message)"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

# Проверяем, что посещение закрыто
Write-Host "
Проверяем статус посещения..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/$visitId" -Method GET -Headers $headers
    Write-Host "Status: $($response.status)"
    Write-Host "Exit time: $($response.exit_time)"
    Write-Host "Duration: $($response.duration_minutes) мин"
} catch {
    Write-Host "ERROR: $($_.ErrorDetails.Message)"
}

Write-Host "
=== Готово! ==="
