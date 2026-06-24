# fix_list_users_call.py
with open('app/api/v1/users.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = '    users = user_service.list_users(offset=offset, limit=limit)'
new_call = '    users = user_service.list_users(offset=offset, limit=limit, role=role)'

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/users.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено: role передаётся в list_users()")
else:
    print("Не найден вызов list_users()")

# Теперь добавляем role в UserService.list_users()
with open('app/services/user_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_service = '    def list_users(self, offset: int = 0, limit: int = 100):'
new_service = '    def list_users(self, offset: int = 0, limit: int = 100, role: str = None):'

if old_service in content:
    content = content.replace(old_service, new_service)
    
    # Добавляем фильтрацию по роли в тело метода
    old_body = '        # получаем список пользователей\n        users = self.db.query(User).offset(offset).limit(limit).all()'
    new_body = '        # получаем запрос\n        query = self.db.query(User)\n        \n        # фильтрация по роли\n        if role:\n            query = query.join(User.user_roles).join(Role).filter(Role.code == role)\n        \n        # получаем список пользователей\n        users = query.offset(offset).limit(limit).all()'
    
    if old_body in content:
        content = content.replace(old_body, new_body)
        print("Фильтрация по роли добавлена в UserService!")
    else:
        print("Не найдено тело метода list_users в UserService")
else:
    print("Не найден метод list_users в UserService")

with open('app/services/user_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
