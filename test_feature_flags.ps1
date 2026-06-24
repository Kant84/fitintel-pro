# test_feature_flags.ps1
# Полный тест Feature Flags

# Получаем токен
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "=== E7a.1 Создание флага (positive) ==="
$body = @{
    flag_key = "test_flag_121909476"
    flag_type = "boolean"
    default_value = "true"
    description = "Test flag"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body

Write-Host "
=== E7a.2 Создание без прав (negative) ==="
# Создадим пользователя без прав и попробуем

Write-Host "
=== E7a.3 Создание дублирующего (negative) ==="
$body = @{
    flag_key = "test_flag_629240844"
    flag_type = "boolean"
    default_value = "true"
} | ConvertTo-Json
$flag1 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body
$flagKey = $flag1.flag_key

$body2 = @{
    flag_key = $flagKey
    flag_type = "boolean"
    default_value = "false"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body2

Write-Host "
=== E7a.4 Проверка флага (positive) ==="
$body = @{
    flag_key = $flagKey
    client_id = "966e13cd-e38b-4641-804e-f69942ccd7dc"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/check" -Method POST -Headers $headers -Body $body

Write-Host "
=== E7a.5 Проверка несуществующего (negative) ==="
$body = @{
    flag_key = "nonexistent_flag_12345"
    client_id = "966e13cd-e38b-4641-804e-f69942ccd7dc"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/check" -Method POST -Headers $headers -Body $body

Write-Host "
=== E7a.6 Bulk-обновление (positive) ==="
$body = @{
    updates = @(
        @{ flag_key = $flagKey; value = "false" }
    )
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/bulk" -Method POST -Headers $headers -Body $body

Write-Host "
=== E7a.7 Аудит изменений (positive) ==="
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/$($flag1.id)/audit" -Method GET -Headers $headers

Write-Host "
=== E7a.14 Недопустимый тип (negative) ==="
$body = @{
    flag_key = "invalid_type_flag"
    flag_type = "invalid"
    default_value = "true"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body

Write-Host "
=== E7a.15 Удаление флага (positive) ==="
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/$($flag1.id)" -Method DELETE -Headers $headers

Write-Host "
=== Готово! ==="
