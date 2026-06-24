# fix_alloweded.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем ALLOWEDED -> ALLOWED
content = content.replace('AccessDecision.ALLOWEDED', 'AccessDecision.ALLOWED')

with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Исправлено: ALLOWEDED -> ALLOWED")
