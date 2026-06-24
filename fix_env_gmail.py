with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('SMTP_HOST=smtp.mail.ru', 'SMTP_HOST=smtp.gmail.com')
content = content.replace('SMTP_PORT=465', 'SMTP_PORT=587')
content = content.replace('SMTP_USER=sanichxxxx@mail.ru', 'SMTP_USER=sanakinandrej4@gmail.com')
content = content.replace('SMTP_FROM_EMAIL=sanichxxxx@mail.ru', 'SMTP_FROM_EMAIL=sanakinandrej4@gmail.com')
# Пароль уже есть в .env: SMTP_PASSWORD=gfhjkmasQQWW!

with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print(".env обновлён для Gmail!")
print("  SMTP_HOST=smtp.gmail.com")
print("  SMTP_PORT=587")
print("  SMTP_USER=sanakinandrej4@gmail.com")
