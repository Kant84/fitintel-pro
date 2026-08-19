# test_first_user_super_admin.ps1
$registerBody = @{
    login = "first_admin_test_$(Get-Random)"
    password = "TestPass123!"
    email = "first_admin@test.com"
} | ConvertTo-Json

Write-Host "=== Регистрация нового пользователя (не первый, т.к. в БД 11 пользователей) ==="
$registerResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register" -Method POST -Body $registerBody -ContentType "application/json"
Write-Host "Пользователь зарегистрирован: $($registerResponse.access_token.Substring(0, 20))..."

Write-Host "
=== Проверка ролей нового пользователя ==="
$loginBody = @{ login = "$($registerBody | ConvertFrom-Json | Select-Object -ExpandProperty login)"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
}

$me = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/me" -Method GET -Headers $headers
Write-Host "Роли пользователя: $($me.roles -join ', ')"
Write-Host "Права пользователя: $($me.permissions -join ', ')"
