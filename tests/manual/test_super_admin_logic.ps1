# test_super_admin_logic.ps1
Write-Host "=== Проверка логики первого пользователя ==="

# Регистрируем нового пользователя (не первый)
$randomLogin = "test_user_$(Get-Random)"
$registerBody = @{
    login = $randomLogin
    password = "TestPass123!"
    email = "$randomLogin@test.com"
} | ConvertTo-Json

$registerResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register" -Method POST -Body $registerBody -ContentType "application/json"
Write-Host "Пользователь $randomLogin зарегистрирован"

# Логинимся
$loginBody = @{ login = $randomLogin; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

# Проверяем роли
$headers = @{ "Authorization" = "Bearer $token" }
$me = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/me" -Method GET -Headers $headers

Write-Host "Роли: $($me.roles -join ', ')"
if ($me.roles -contains 'SUPER_ADMIN') {
    Write-Host "ERROR: Пользователь получил SUPER_ADMIN, хотя не является первым!"
} else {
    Write-Host "OK: Пользователь НЕ получил SUPER_ADMIN (корректно, т.к. не первый)"
}

# Удаляем тестового пользователя
Write-Host "
Удаляем тестового пользователя..."
psql -h 127.0.0.1 -U postgres -d fitnexus -c "DELETE FROM user_roles WHERE user_id = (SELECT id FROM users WHERE username = '$randomLogin');"
psql -h 127.0.0.1 -U postgres -d fitnexus -c "DELETE FROM users WHERE username = '$randomLogin';"
Write-Host "Тестовый пользователь удалён"
