# Проверим текущий .env
Get-Content .env | Select-String "SMTP|MAIL" -Context 0,0
