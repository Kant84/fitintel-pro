# fix_user_filter.py
with open('app/api/v1/users.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим list_users и добавляем параметр role
old_list = '''@router.get("/", response_model=UserListResponse)
def list_users(
    # Смещение для пагинации.
    offset: int = Query(default=0, ge=0),

    # Максимальное количество записей.
    limit: int = Query(default=100, ge=1, le=200),'''

new_list = '''@router.get("/", response_model=UserListResponse)
def list_users(
    # Смещение для пагинации.
    offset: int = Query(default=0, ge=0),

    # Максимальное количество записей.
    limit: int = Query(default=100, ge=1, le=200),

    # Фильтрация по роли.
    role: str | None = Query(default=None),'''

if old_list in content:
    content = content.replace(old_list, new_list)
    
    # Теперь добавляем фильтрацию в тело функции
    old_body = '''    # получаем сервис пользователей
    user_service = UserService(db)

    # получаем список пользователей
    users = user_service.list_users(offset=offset, limit=limit)'''
    
    new_body = '''    # получаем сервис пользователей
    user_service = UserService(db)

    # получаем список пользователей
    users = user_service.list_users(offset=offset, limit=limit, role=role)'''
    
    if old_body in content:
        content = content.replace(old_body, new_body)
        print("Фильтрация по роли добавлена в endpoint!")
    else:
        print("Не найдено тело функции list_users")
else:
    print("Не найдена сигнатура list_users")

with open('app/api/v1/users.py', 'w', encoding='utf-8') as f:
    f.write(content)
