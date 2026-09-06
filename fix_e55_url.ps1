# fix_e55_url.ps1 — замена _e55_url в client.py
# Запуск: .\fix_e55_url.ps1

$path = "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop\api\client.py"

if (-not (Test-Path $path)) {
    Write-Host "❌ Файл не найден: $path" -ForegroundColor Red
    exit 1
}

# Бэкап
$backup = $path + ".backup_" + (Get-Date -Format "yyyyMMdd_HHmmss")
Copy-Item $path $backup
Write-Host "✅ Бэкап создан: $backup" -ForegroundColor Green

$content = Get-Content $path -Raw -Encoding UTF8

# Старый блок (точное совпадение)
$old = @"
def _e55_url(self, path):
    base = (getattr(self, "base_url", None) or getattr(self, "base", None)
            or getattr(self, "BASE_URL", None) or "http://localhost:8001")
    return str(base).rstrip("/") + "/api/v1" + path
"@

# Новый блок
$new = @"
def _e55_url(self, path):
    base = (getattr(self, "base_url", None) or getattr(self, "base", None)
            or getattr(self, "BASE_URL", None) or "http://localhost:8001")
    base = str(base).rstrip("/")
    if base.endswith("/api/v1"):
        return base + path
    return base + "/api/v1" + path
"@

if ($content.Contains($old)) {
    $content = $content.Replace($old, $new)
    Set-Content $path $content -Encoding UTF8 -NoNewline
    Write-Host "✅ _e55_url исправлен! Перезапустите desktop-клиент." -ForegroundColor Green
} else {
    Write-Host "⚠️  Старый блок _e55_url не найден. Возможно, файл уже изменён." -ForegroundColor Yellow
    Write-Host "   Проверьте вручную: $path" -ForegroundColor Yellow
}