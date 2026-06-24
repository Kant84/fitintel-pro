import re

with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем SMTP-настройки
replacements = {
    'SMTP_HOST=': 'SMTP_HOST=mail.fixintel.ru',
    'SMTP_USER=': 'SMTP_USER=info@fixintel.ru',
    'SMTP_FROM_NAME=': 'SMTP_FROM_NAME=FitIntel PRO',
    'SMTP_FROM_EMAIL=': 'SMTP_FROM_EMAIL=info@fixintel.ru',
}

for old, new in replacements.items():
    if old in content and old + '\n' in content:
        content = content.replace(old + '\n', new + '\n')
    elif old in content:
        content = content.replace(old, new)

with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print(".env обновлён!")
print("ВНИМАНИЕ: Введи пароль от info@fixintel.ru в .env:")
print("  SMTP_PASSWORD=твой_пароль")
print("Потом перезапусти сервер!")
