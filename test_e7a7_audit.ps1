# test_e7a7_audit.ps1
Write-Host "=== E7a.7 Аудит изменений (positive) ==="

# Логинимся как SUPER_ADMIN
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создаём флаг для теста
Write-Host "Создаём тестовый флаг..."
$body = @{
    name = "Audit Test Flag"
    flag_key = "audit_test_flag"
    flag_type = "boolean"
    default_value = "true"
} | ConvertTo-Json

$flag = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body
$flagId = $flag.id
Write-Host "Флаг создан, ID: $flagId"

# Обновляем флаг (чтобы создать запись в аудите)
Write-Host "
Обновляем флаг..."
$updateBody = @{
    target_value = "false"
    changed_by = "my_new_username"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/$flagId" -Method PUT -Headers $headers -Body $updateBody | Out-Null
Write-Host "Флаг обновлён"

# Проверяем аудит
Write-Host "
Получаем аудит изменений..."
try {
    $audit = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/$flagId/audit" -Method GET -Headers $headers
    Write-Host "OK: Аудит получен"
    Write-Host "Записей в аудите: $($audit.Count)"
    foreach ($record in $audit) {
        Write-Host "  - Действие: $($record.action), Старое значение: $($record.old_value), Новое значение: $($record.new_value), Кем: $($record.changed_by)"
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}

# Удаляем тестовый флаг
Write-Host "
Удаляем тестовый флаг..."
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/$flagId" -Method DELETE -Headers $headers | Out-Null
Write-Host "Тестовый флаг удалён"
