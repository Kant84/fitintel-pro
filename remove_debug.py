# remove_debug.py
with open('app/api/dependencies.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_debug = '''        # DEBUG
        print(f"DEBUG: user_roles={user_roles}, type={type(user_roles)}")
        print(f"DEBUG: required_roles={required_roles}, type={type(required_roles)}")
        for i, r in enumerate(required_roles):
            print(f"DEBUG: required_roles[{i}]={r}, type={type(r)}")
        
        # если пересечения нет, возвращаем 403'''

new_debug = '''        # если пересечения нет, возвращаем 403'''

if old_debug in content:
    content = content.replace(old_debug, new_debug)
    with open('app/api/dependencies.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG убран!")
else:
    print("DEBUG не найден")
