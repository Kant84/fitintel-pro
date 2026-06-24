# fix_dependencies.py
with open('app/api/dependencies.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_roles = '''        # получаем роли пользователя
        user_roles = set(auth_service.get_user_roles(current_user))'''

new_roles = '''        # получаем роли пользователя
        raw_roles = auth_service.get_user_roles(current_user)
        # извлекаем code из объектов Role (или строк, если уже строки)
        user_roles = set()
        for r in raw_roles:
            if hasattr(r, 'code'):
                user_roles.add(r.code)
            else:
                user_roles.add(str(r))'''

if old_roles in content:
    content = content.replace(old_roles, new_roles)
    with open('app/api/dependencies.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("dependencies.py исправлен!")
else:
    print("ERROR: Не найдена строка")
