"""Проверка входа программно (без desktop)"""
import sys
sys.path.insert(0, ".")
import app.main
from app.db.session import SessionLocal
from app.services.auth_service import AuthService

login = input("Логин: ").strip()
password = input("Пароль: ").strip()

db = SessionLocal()
auth = AuthService(db)
user = auth.authenticate_user(login, password)

if user is None:
    print("FAIL: сервер не принимает такую пару логин/пароль")
else:
    print(f"OK: вход выполнен, user_id={user.id}")
    print(f"     is_active={user.is_active}, locked_until={getattr(user, 'locked_until', None)}")