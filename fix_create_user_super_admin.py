# fix_create_user_super_admin.py
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_create = '''        # добавляем в БД
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user'''

new_create = '''        # добавляем в БД
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Проверяем, является ли пользователь первым в системе
        # Если да — автоматически назначаем роль SUPER_ADMIN
        user_count = self.db.query(User).count()
        if user_count == 1:
            # Получаем или создаём роль SUPER_ADMIN
            from app.models.role import Role
            from app.models.user_role import UserRole
            
            super_admin_role = self.db.query(Role).filter(Role.code == 'SUPER_ADMIN').first()
            if not super_admin_role:
                super_admin_role = Role(
                    code='SUPER_ADMIN',
                    name='Super Administrator',
                    description='Полный доступ к системе',
                    is_system=True
                )
                self.db.add(super_admin_role)
                self.db.commit()
                self.db.refresh(super_admin_role)
            
            # Назначаем роль пользователю
            user_role = UserRole(
                user_id=user.id,
                role_id=super_admin_role.id,
                assigned_at=datetime.utcnow()
            )
            self.db.add(user_role)
            self.db.commit()
        
        return user'''

if old_create in content:
    content = content.replace(old_create, new_create)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("create_user исправлен — первый пользователь получает SUPER_ADMIN!")
else:
    print("ERROR: Не найдена строка")
