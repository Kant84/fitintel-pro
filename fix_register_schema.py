# fix_register_schema.py
# Добавление RegisterRequest с email и исправление auth.py

import re

# 1. Добавляем RegisterRequest в schemas/auth.py
with open('app/schemas/auth.py', 'r', encoding='utf-8') as f:
    schema_content = f.read()

# Проверяем, есть ли уже RegisterRequest
if 'class RegisterRequest' not in schema_content:
    # Находим место после LoginRequest
    insert_point = schema_content.find('class TokenResponse')
    if insert_point != -1:
        new_schema = '''# схема регистрации с email
class RegisterRequest(BaseModel):
    # логин пользователя
    login: str
    
    # пароль пользователя
    password: str
    
    # email пользователя (опционально)
    email: str | None = None
    
    # телефон пользователя (опционально)
    phone: str | None = None
    
    # полное имя (опционально)
    full_name: str | None = None


'''
        schema_content = schema_content[:insert_point] + new_schema + schema_content[insert_point:]
        
        with open('app/schemas/auth.py', 'w', encoding='utf-8') as f:
            f.write(schema_content)
        print("RegisterRequest добавлен в schemas/auth.py")
    else:
        print("Не найдено место для RegisterRequest")
else:
    print("RegisterRequest уже существует")

# 2. Исправляем auth.py - используем RegisterRequest и передаём email
with open('app/api/v1/auth.py', 'r', encoding='utf-8') as f:
    auth_content = f.read()

# Заменяем импорт LoginRequest на RegisterRequest для register endpoint
old_import = 'from app.schemas.auth import LoginRequest, TokenResponse'
new_import = 'from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse'

if old_import in auth_content:
    auth_content = auth_content.replace(old_import, new_import)
    print("Импорт RegisterRequest добавлен")
else:
    print("Импорт не найден, проверьте вручную")

# Заменяем payload тип и добавляем email
old_register = '''@router.post("/register", response_model=TokenResponse)
def register(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Регистрация нового пользователя"""
    # создаём сервис аутентификации
    auth_service = AuthService(db)
    
    # проверяем, существует ли пользователь
    existing = auth_service.get_user_by_login(payload.login)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # создаём пользователя
    user = auth_service.create_user(payload.login, payload.password)'''

new_register = '''@router.post("/register", response_model=TokenResponse)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Регистрация нового пользователя"""
    # создаём сервис аутентификации
    auth_service = AuthService(db)
    
    # проверяем, существует ли пользователь по логину
    existing = auth_service.get_user_by_login(payload.login)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # проверяем, существует ли пользователь по email
    if payload.email:
        existing_email = auth_service.get_user_by_email(payload.email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")
    
    # создаём пользователя с email
    user = auth_service.create_user(payload.login, payload.password, payload.email)'''

if old_register in auth_content:
    auth_content = auth_content.replace(old_register, new_register)
    print("register endpoint исправлен")
else:
    print("register endpoint не найден, проверьте вручную")

# 3. Добавляем get_user_by_email в auth_service.py (если нет)
with open('app/services/auth_service.py', 'r', encoding='utf-8') as f:
    service_content = f.read()

if 'def get_user_by_email' not in service_content:
    # Находим метод get_user_by_login и добавляем после него
    insert_point = service_content.find('def get_user_by_login')
    if insert_point != -1:
        # Находим конец метода get_user_by_login
        next_def = service_content.find('def ', insert_point + 1)
        if next_def != -1:
            new_method = '''
    # метод ищет пользователя по email
    def get_user_by_email(self, email: str):
        # импортируем модель пользователя
        from app.models.user import User
        
        # ищем пользователя по email
        return self.db.query(User).filter(User.email == email).first()

'''
            service_content = service_content[:next_def] + new_method + service_content[next_def:]
            
            with open('app/services/auth_service.py', 'w', encoding='utf-8') as f:
                f.write(service_content)
            print("get_user_by_email добавлен в auth_service.py")
        else:
            print("Не найдено место для get_user_by_email")
    else:
        print("get_user_by_login не найден")
else:
    print("get_user_by_email уже существует")

with open('app/api/v1/auth.py', 'w', encoding='utf-8') as f:
    f.write(auth_content)

print("Фикс завершён! Перезапустите сервер.")
