#!/usr/bin/env python
"""Скрипт для создания администратора"""

import sys
import os
import getpass
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.user_service import UserService


def create_admin():
    admin_email = os.environ.get("FITINTEL_ADMIN_EMAIL", "").strip()
    if not admin_email and sys.stdin.isatty():
        admin_email = input("Admin email: ").strip()
    if not admin_email:
        raise RuntimeError("Set FITINTEL_ADMIN_EMAIL or run interactively")

    admin_username = os.environ.get("FITINTEL_ADMIN_USERNAME", "").strip()
    if not admin_username:
        admin_username = admin_email

    admin_password = os.environ.get("FITINTEL_ADMIN_PASSWORD")
    if not admin_password and sys.stdin.isatty():
        admin_password = getpass.getpass("Admin password: ")
    if not admin_password:
        raise RuntimeError("Set FITINTEL_ADMIN_PASSWORD or run interactively")
    if len(admin_password) < 8:
        raise ValueError("FITINTEL_ADMIN_PASSWORD must contain at least 8 characters")
    db = SessionLocal()
    try:
        user_service = UserService(db)
        
        # Проверяем, есть ли уже admin
        existing = user_service.user_repository.get_by_email(admin_email)
        if existing:
            print("Администратор уже существует!")
            return
        
        # Создаём администратора
        admin = user_service.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_superuser=True,
            is_active=True,
            is_verified=True,
        )
        
        print("Операция выполнена.")
        
    except Exception:
        print("Admin creation failed.")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()