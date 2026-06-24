# fix_indentation.py
# Исправление отступов в auth_service.py

with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Исправляем строку 163 (create_user) - добавляем отступ
# Находим строку с "def create_user" без отступа
for i, line in enumerate(lines):
    if line.startswith('def create_user(self, login: str, password: str)'):
        lines[i] = '    ' + line
        print(f"Исправлена строка {i+1}: добавлен отступ к create_user")
        break

# Проверяем, все ли методы класса имеют правильные отступы
fixed_count = 0
for i, line in enumerate(lines):
    # Методы класса должны иметь отступ 4 пробела
    if line.startswith('def ') and not line.startswith('    def '):
        # Проверяем, что это метод AuthService (не вложенная функция)
        if 'self' in line:
            lines[i] = '    ' + line
            fixed_count += 1
            print(f"Исправлена строка {i+1}: {line.strip()}")

with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"Исправлено {fixed_count} строк")
print("Готово! Перезапустите сервер.")
