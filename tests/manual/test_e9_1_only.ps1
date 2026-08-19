# test_e9_1_only.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E9.1 — Открытие по карте (positive) ==="

# Логинимся
$loginBody = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
$token = $loginResponse.access_token

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$deviceId = "turnstile_test_de2736"

$body = @{ credential = "qr_code_payload_12345"; device_id = $deviceId; zone = "GYM" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/access/open" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "OK: granted=$($r.granted), turnstile_open=$($r.turnstile_open)"
    if ($r.visit_id) {
        Write-Host "  visit_id=$($r.visit_id)"
        # Выходим
        $exitBody = @{ visit_id = $r.visit_id } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://localhost:8001/api/v1/visits/check-out" -Method POST -Headers $headers -Body ([System.Text.Encoding]::UTF8.GetBytes($exitBody)) | Out-Null
        Write-Host "  Выход выполнен"
    }
} catch { Write-Host "ERROR: $($_.ErrorDetails.Message)" }

Write-Host "
=== Готово! ==="
