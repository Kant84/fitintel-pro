# fix_access_decision.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем AccessDecision.ALLOW на AccessDecision.ALLOWED
content = content.replace('AccessDecision.ALLOW,', 'AccessDecision.ALLOWED,')

with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Исправлено: AccessDecision.ALLOW -> AccessDecision.ALLOWED")
