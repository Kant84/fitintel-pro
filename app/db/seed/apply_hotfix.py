# app/db/seed/apply_hotfix.py
"""Хотфикс v1.5.1: недостающие permissions + superadmin (upsert) + роль admin.
Запуск: python -m app.db.seed.apply_hotfix (в контейнере api)."""
import os
from uuid import uuid4

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.user import User
from app.db.seed.seed_permissions import seed_permissions
from app.core.security import get_password_hash

SUPERADMIN_USERNAME = os.environ.get("SUPERADMIN_USERNAME")
SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD")


def run():
    credentials = {
        "SUPERADMIN_USERNAME": SUPERADMIN_USERNAME,
        "SUPERADMIN_EMAIL": SUPERADMIN_EMAIL,
        "SUPERADMIN_PASSWORD": SUPERADMIN_PASSWORD,
    }
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        raise RuntimeError("Missing required seed environment variables: " + ", ".join(missing))
    if len(SUPERADMIN_PASSWORD) < 12:
        raise ValueError("SUPERADMIN_PASSWORD must contain at least 12 characters")
    db = SessionLocal()
    try:
        # 1. Добиваем permissions (devices/setup/services/documents/face/ui)
        seed_permissions(db)
        print("OK: permissions обновлены")

        # 2. Создаём или обновляем superadmin (хеш — штатной схемой pbkdf2_sha256)
        pwd = get_password_hash(SUPERADMIN_PASSWORD)
        existing = db.query(User).filter(User.username == SUPERADMIN_USERNAME).first()
        if not existing:
            db.add(User(
                id=str(uuid4()),
                username=SUPERADMIN_USERNAME,
                email=SUPERADMIN_EMAIL,
                password_hash=pwd,
                is_active=True,
                is_superuser=True,
                is_verified=True,
                failed_login_count=0,
                locked_until=None,
            ))
            db.commit()
            print("Операция выполнена.")
        else:
            existing.email = SUPERADMIN_EMAIL   # был .local — ломал /auth/me (Pydantic EmailStr)
            existing.password_hash = pwd
            existing.is_active = True
            existing.is_superuser = True
            existing.is_verified = True
            existing.failed_login_count = 0
            existing.locked_until = None
            db.commit()
            print("Операция выполнена.")

        # 3. Назначаем роль admin superadmin'у (без роли часть эндпоинтов падает 500)
        db.execute(text(
            "INSERT INTO user_roles (id, user_id, role_id, assigned_at, created_at, updated_at) "
            "SELECT gen_random_uuid(), u.id, r.id, now(), now(), now() "
            "FROM users u, roles r "
            "WHERE u.username = 'superadmin' AND r.code = 'admin' "
            "ON CONFLICT (user_id, role_id) DO NOTHING"
        ))
        db.commit()
        print("Операция выполнена.")
    finally:
        db.close()


if __name__ == "__main__":
    run()