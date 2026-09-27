# app/db/seed/apply_hotfix.py
"""Хотфикс v1.5.1: недостающие permissions + пользователь superadmin.
Запуск: python -m app.db.seed.apply_hotfix (в контейнере api)."""
from uuid import uuid4

import bcrypt

from app.db.session import SessionLocal
from app.models.user import User
from app.db.seed.seed_permissions import seed_permissions


def run():
    db = SessionLocal()
    try:
        # 1. Добиваем permissions (devices/setup/services/documents/face/ui)
        seed_permissions(db)
        print("OK: permissions обновлены")

        # 2. Создаём superadmin, если отсутствует
        if not db.query(User).filter(User.username == "superadmin").first():
            db.add(User(
                id=str(uuid4()),
                username="superadmin",
                email="superadmin@fitintel.local",
                password_hash=bcrypt.hashpw("g96PUkT7yP".encode(),
                                            bcrypt.gensalt()).decode(),
                is_active=True,
                is_superuser=True,
                is_verified=True,
            ))
            db.commit()
            print("OK: superadmin создан")
        else:
            print("SKIP: superadmin уже существует")
    finally:
        db.close()


if __name__ == "__main__":
    run()