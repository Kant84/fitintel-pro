# fix_auth_import.py
# Добавление импорта схем в auth.py

with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Проверяем, есть ли уже импорт схем
if 'from app.schemas.auth import' not in content:
    # Находим место после импорта security
    insert_point = content.find('from app.core.security import')
    if insert_point != -1:
        # Находим конец строки
        line_end = content.find('\n', insert_point)
        if line_end != -1:
            new_import = '''

# импорт схем аутентификации
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse'''
            content = content[:line_end+1] + new_import + content[line_end+1:]
            
            with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Импорт схем добавлен в auth.py")
        else:
            print("Не найден конец строки импорта security")
    else:
        print("Не найден импорт security")
else:
    # Проверяем, есть ли RegisterRequest в импорте
    if 'RegisterRequest' not in content:
        # Добавляем RegisterRequest в существующий импорт
        old_import = 'from app.schemas.auth import LoginRequest, TokenResponse'
        new_import = 'from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse'
        if old_import in content:
            content = content.replace(old_import, new_import)
            with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("RegisterRequest добавлен в импорт")
        else:
            print("Не найден старый импорт для замены")
    else:
        print("RegisterRequest уже в импорте")
