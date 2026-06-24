# Добавляем SMTP-настройки mailcow в .env
 = @'
# 9. Email (SMTP)
SMTP_HOST=mail.fixintel.ru
SMTP_PORT=587
SMTP_USER=noreply@fixintel.ru
SMTP_PASSWORD=FitNexus_Postgres_2026!
SMTP_TLS=true
SMTP_FROM_NAME=FitIntel PRO
SMTP_FROM_EMAIL=noreply@fixintel.ru
'@

# Проверяем, есть ли уже SMTP-блок
 = Get-Content .env -Raw
if ( -match "SMTP_HOST=") {
    # Заменяем пустые значения
     =  -replace "SMTP_HOST=", "SMTP_HOST=mail.fixintel.ru"
     =  -replace "SMTP_USER=", "SMTP_USER=noreply@fixintel.ru"
     =  -replace "SMTP_PASSWORD=", "SMTP_PASSWORD=FitNexus_Postgres_2026!"
     =  -replace "SMTP_FROM_NAME=", "SMTP_FROM_NAME=FitIntel PRO"
     =  -replace "SMTP_FROM_EMAIL=", "SMTP_FROM_EMAIL=noreply@fixintel.ru"
     | Set-Content .env -Encoding utf8
    Write-Host ".env updated!"
} else {
    Add-Content .env -Value  -Encoding utf8
    Write-Host "SMTP added to .env!"
}
