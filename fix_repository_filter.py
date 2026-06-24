# fix_repository_filter.py
with open('app/repositories/user_repository.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем role в сигнатуру
old_sig = '''    def list_with_roles_permissions(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[User]:'''

new_sig = '''    def list_with_roles_permissions(
        self,
        offset: int = 0,
        limit: int = 100,
        role: str = None,
    ) -> list[User]:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    
    # Добавляем фильтрацию по роли
    old_filter = '''            # сортируем по username для стабильного результата
            .order_by(User.username)
            # применяем offset'''
    
    new_filter = '''            # фильтрация по роли
            if role:
                statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
            
            # сортируем по username для стабильного результата
            statement = statement.order_by(User.username)
            # применяем offset'''
    
    if old_filter in content:
        content = content.replace(old_filter, new_filter)
        print("Фильтрация по роли добавлена в репозиторий!")
    else:
        print("Не найдено место для фильтрации")
else:
    print("Не найдена сигнатура list_with_roles_permissions")

with open('app/repositories/user_repository.py', 'w', encoding='utf-8') as f:
    f.write(content)
