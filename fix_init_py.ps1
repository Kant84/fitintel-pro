# Сначала сохраняем текущее содержимое
$initPath = "app/api/v1/__init__.py"
$content = Get-Content $initPath -Raw

# Добавляем импорт и регистрацию
$newContent = $content -replace '(from app.api.v1 import services, auth, users, exports, analytics, devices)', '$0, dynamic_qr'
$newContent = $newContent -replace '(router\.include_router\(devices\.router, tags=\["Devices"\])', '$0`nrouter.include_router(dynamic_qr.router, tags=["Dynamic QR"])'

Set-Content -Path $initPath -Value $newContent -NoNewline
Write-Host "✅ dynamic_qr добавлен в __init__.py"
