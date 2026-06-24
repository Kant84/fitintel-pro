# fix_account_lockout.py
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_auth = '''    def authenticate_user(self, login: str, password: str):
        # получаем пользователя по логину
        user = self.get_user_by_login(login)
        
        # если пользователь не найден, вызываем исключение
        if not user:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # проверяем пароль
        if not verify_password(password, self.get_user_password_hash(user)):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # проверяем, активен ли пользователь
        if not self.is_user_active(user):
            raise HTTPException(status_code=403, detail="Пользователь заблокирован")'''

new_auth = '''    def authenticate_user(self, login: str, password: str):
        # получаем пользователя по логину
        user = self.get_user_by_login(login)
        
        # если пользователь не найден, вызываем исключение
        if not user:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # проверяем, не заблокирован ли пользователь
        from datetime import datetime, timezone
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail="Аккаунт заблокирован. Попробуйте позже.")
        
        # проверяем пароль
        if not verify_password(password, self.get_user_password_hash(user)):
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                from datetime import datetime, timezone, timedelta
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                user.failed_login_count = 0
                self.db.commit()
                raise HTTPException(status_code=423, detail="Аккаунт заблокирован на 15 минут")
            self.db.commit()
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # сбрасываем счётчик при успехе
        user.failed_login_count = 0
        self.db.commit()
        
        # проверяем, активен ли пользователь
        if not self.is_user_active(user):
            raise HTTPException(status_code=403, detail="Пользователь заблокирован")'''

if old_auth in content:
    content = content.replace(old_auth, new_auth)
    with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Блокировка добавлена!")
else:
    print("Не найден метод для замены")
