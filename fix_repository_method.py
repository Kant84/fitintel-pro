# fix_repository_method.py
with open('app/repositories/user_repository.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_method = '''    def list_with_roles_permissions(
        self,
        offset: int = 0,
        limit: int = 100,
        role: str = None,
    ) -> list[User]:
        # создаём SQL-запрос
        statement = (
            select(User)
            .options(
                # загружаем связи user_roles
                selectinload(User.user_roles)
                # внутри связи загружаем роль
                .selectinload(UserRole.role)
                # внутри роли загружаем связи role_permissions
                .selectinload(Role.role_permissions)
                # внутри связи загружаем permission
                .selectinload(RolePermission.permission)
            )
            # фильтрация по роли
            if role:
                statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
            
            # сортируем по username для стабильного результата
            statement = statement.order_by(User.username)
            # применяем offset и limit
            statement = statement.offset(offset).limit(limit)
        )

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список пользователей
        return list(result.scalars().all())'''

new_method = '''    def list_with_roles_permissions(
        self,
        offset: int = 0,
        limit: int = 100,
        role: str = None,
    ) -> list[User]:
        # создаём SQL-запрос
        statement = select(User).options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
        
        # фильтрация по роли
        if role:
            statement = statement.join(User.user_roles).join(UserRole.role).where(Role.code == role)
        
        # сортируем по username для стабильного результата
        statement = statement.order_by(User.username)
        # применяем offset и limit
        statement = statement.offset(offset).limit(limit)

        # выполняем запрос
        result = self.db.execute(statement)

        # возвращаем список пользователей
        return list(result.scalars().all())'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('app/repositories/user_repository.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Метод исправлен!")
else:
    print("Не найден метод для замены")
