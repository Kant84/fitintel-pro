with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем SMTP-настройки
content = content.replace('SMTP_HOST=mail.fixintel.ru', 'SMTP_HOST=smtp.mail.ru')
content = content.replace('SMTP_PORT=587', 'SMTP_PORT=465')
content = content.replace('SMTP_USER=info@fixintel.ru', 'SMTP_USER=sanichxxxx@mail.ru')
content = content.replace('SMTP_FROM_EMAIL=info@fixintel.ru', 'SMTP_FROM_EMAIL=sanichxxxx@mail.ru')

with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print(".env обновлён!")
print("Проверь:")
print("  SMTP_HOST=smtp.mail.ru")
print("  SMTP_PORT=465")
print("  SMTP_USER=sanichxxxx@mail.ru")
