# test_e7a6_bulk_update_v2.ps1
Write-Host "=== E7a.6 Bulk-обновление флагов (positive) ==="

# Логинимся как SUPER_ADMIN
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Создадим два флага для теста
Write-Host "Создаём тестовые флаги..."

$body1 = @{
    name = "Bulk Flag 1"
    flag_key = "bulk_flag_1"
    flag_type = "boolean"
    default_value = "true"
} | ConvertTo-Json

try {
    $flag1 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body1
    Write-Host "Флаг 1 создан: $($flag1.flag_key)"
} catch {
    Write-Host "ERROR создания флага 1: $($_.Exception.Message)"
}

$body2 = @{
    name = "Bulk Flag 2"
    flag_key = "bulk_flag_2"
    flag_type = "boolean"
    default_value = "false"
} | ConvertTo-Json

try {
    $flag2 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers $headers -Body $body2
    Write-Host "Флаг 2 создан: $($flag2.flag_key)"
} catch {
    Write-Host "ERROR создания флага 2: $($_.Exception.Message)"
}

# Bulk-обновление
Write-Host "
Выполняем bulk-обновление..."
$bulkBody = @{
    flags = @(
        @{
            flag_key = "bulk_flag_1"
            target_value = "false"
        },
        @{
            flag_key = "bulk_flag_2"
            target_value = "true"
        }
    )
    changed_by = "my_new_username"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/bulk" -Method POST -Headers $headers -Body $bulkBody
    Write-Host "OK: Bulk-обновление выполнено"
    Write-Host "Обновлено флагов: $($response.updated)"
    if ($response.errors.Count -gt 0) {
        Write-Host "Ошибки: $($response.errors -join ', ')"
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}

# Проверяем результат
Write-Host "
Проверяем результат..."
psql -h 127.0.0.1 -U postgres -d fitnexus -c "SELECT flag_key, target_value FROM feature_flags WHERE flag_key IN ('bulk_flag_1', 'bulk_flag_2');"

# Удаляем тестовые флаги
Write-Host "
Удаляем тестовые флаги..."
psql -h 127.0.0.1 -U postgres -d fitnexus -c "DELETE FROM feature_flag_audit WHERE flag_id IN (SELECT id FROM feature_flags WHERE flag_key IN ('bulk_flag_1', 'bulk_flag_2'));" 2>$null
psql -h 127.0.0.1 -U postgres -d fitnexus -c "DELETE FROM feature_flags WHERE flag_key IN ('bulk_flag_1', 'bulk_flag_2');" 2>$null
Write-Host "Тестовые флаги удалены"
