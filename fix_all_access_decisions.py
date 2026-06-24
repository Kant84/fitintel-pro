# fix_all_access_decisions.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем все неверные значения
content = content.replace('AccessDecision.DENY', 'AccessDecision.DENIED')
content = content.replace('AccessDecision.ALLOW', 'AccessDecision.ALLOWED')

with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Исправлено: DENY -> DENIED, ALLOW -> ALLOWED")
