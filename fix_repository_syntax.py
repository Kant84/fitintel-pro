# fix_repository_syntax.py
with open('app/repositories/user_repository.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''            # фильтрация по роли
            if role:
                statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
            
            # сортируем по username для стабильного результата
            statement = statement.order_by(User.username)
            # применяем offset
            .offset(offset)
            # применяем limit
            .limit(limit)
        )'''

new_code = '''            # фильтрация по роли
            if role:
                statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
            
            # сортируем по username для стабильного результата
            statement = statement.order_by(User.username)
            # применяем offset и limit
            statement = statement.offset(offset).limit(limit)
        )'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app/repositories/user_repository.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Синтаксис исправлен!")
else:
    print("Не найден блок для замены")
