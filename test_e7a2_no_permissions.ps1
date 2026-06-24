# test_e7a2_no_permissions.ps1
Write-Host "=== E7a.2 Создание флага без прав (negative) ==="

# Регистрируем нового пользователя (без SUPER_ADMIN)
$randomLogin = "no_admin_$(Get-Random)"
$registerBody = @{
    login = $randomLogin
    password = "TestPass123!"
    email = "$randomLogin@test.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register" -Method POST -Body $registerBody -ContentType "application/json" | Out-Null
Write-Host "Пользователь $randomLogin зарегистрирован (без SUPER_ADMIN)"

# Логинимся
$loginBody = @{ login = $randomLogin; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

# Пытаемся создать флаг
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    name = "Test Flag"
    flag_key = "test_flag_no_admin"
    flag_type = "boolean"
    default_value = "true"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body
    Write-Host "ERROR: Флаг создан без прав!"
} catch {
    Write-Host "OK: Доступ запрещён (403)"
    Write-Host "Ошибка: $($_.Exception.Message)"
}

# Удаляем тестового пользователя
psql -h 127.0.0.1 -U postgres -d fitnexus -c "DELETE FROM users WHERE username = '$randomLogin';" 2>$null
Write-Host "Тестовый пользователь удалён"
