# fix_password_validation.py
with open('app/schemas/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем password: str на password с валидацией
old_password = '''    # пароль пользователя
    password: str'''
    
new_password = '''    # пароль пользователя
    password: str = Field(min_length=8, max_length=128)'''

if old_password in content:
    content = content.replace(old_password, new_password)
    print("Валидация пароля добавлена!")
else:
    print("Не найдено поле password для замены")

with open('app/schemas/auth.py', 'w', encoding='utf-8') as f:
    f.write(content)
