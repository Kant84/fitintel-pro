#!/usr/bin/env python
"""Скрипт для создания администратора"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.audit_service import AuditService
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    db = SessionLocal()
    try:
        user_service = UserService(db)
        role_service = RoleService(db)
        
        # Проверяем, есть ли уже admin
        existing = user_service.get_user_by_email("admin@fitnexus.com")
        if existing:
            print("Администратор уже существует!")
            return
        
        # Создаём администратора
        admin = user_service.create_user(
            email="admin@fitnexus.com",
            password="Admin123!",
            is_superuser=True,
            is_active=True,
            is_verified=True,
        )
        
        print(f"✅ Администратор создан: admin@fitnexus.com / Admin123!")
        print(f"ID: {admin.id}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()