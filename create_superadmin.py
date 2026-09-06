"""Создание SuperAdmin для первого входа"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Загружаем ВСЁ приложение (все модели)
import app.main  # ← это загрузит все модели SQLAlchemy

from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.core.security import get_password_hash

db = SessionLocal()
auth = AuthService(db)

existing = auth.get_user_by_login("SuperAdmin")
if existing:
    print("SuperAdmin уже существует!")
else:
    user = auth.create_user("SuperAdmin", "qPywFZf9rl", "admin@fitintel.local")
    user.role = "superadmin"
    user.is_active = True
    user.full_name = "Администратор"
    db.commit()
    print(f"SuperAdmin создан! ID: {user.id}")

db.close()