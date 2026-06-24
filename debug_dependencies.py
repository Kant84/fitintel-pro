# debug_dependencies.py
with open('app/api/dependencies.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''        # если пересечения нет, возвращаем 403
        if not user_roles.intersection(set(required_roles)):'''

new_check = '''        # DEBUG
        print(f"DEBUG: user_roles={user_roles}, type={type(user_roles)}")
        print(f"DEBUG: required_roles={required_roles}, type={type(required_roles)}")
        for i, r in enumerate(required_roles):
            print(f"DEBUG: required_roles[{i}]={r}, type={type(r)}")
        
        # если пересечения нет, возвращаем 403
        if not user_roles.intersection(set(required_roles)):'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/api/dependencies.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG добавлен!")
else:
    print("ERROR: Не найдена строка")
