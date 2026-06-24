# fix_create_user_signature.py
# Добавление email в сигнатуру create_user

with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем сигнатуру
old = '    def create_user(self, login: str, password: str):'
new = '    def create_user(self, login: str, password: str, email: str = None):'

if old in content:
    content = content.replace(old, new)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Сигнатура create_user исправлена! Добавлен email: str = None")
else:
    print("Не найдена старая сигнатура!")
    print("Текущая сигнатура:")
    import re
    match = re.search(r'def create_user\([^)]+\):', content)
    if match:
        print(match.group())
