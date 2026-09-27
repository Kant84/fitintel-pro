# app/db/seed/apply_hotfix.py
"""Хотфикс v1.5.1: недостающие permissions + superadmin.
Запуск: python -m app.db.seed.apply_hotfix (в контейнере api)."""
from uuid import uuid4
from datetime import datetime, timezone
from passlib.context import CryptContext

from app.db.session import SessionLocal
from app.models.user import User
from app.db.seed.seed_permissions import seed_permissions


def run():
    db = SessionLocal()
    try:
        seed_permissions(db)
        print("OK: permissions обновлены")
        if not db.query(User).filter(User.username == "superadmin").first():
            db.add(User(
                id=str(uuid4()),
                username="superadmin",
                email="superadmin@fitintel.local",
                hashed_password=CryptContext(schemes=["bcrypt"], deprecated="auto")
                                    .hash("g96PUkT7yP"),
                first_name="SuperAdmin",
                last_name="FitIntel",
                is_active=True,
                is_superuser=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
            db.commit()
            print("OK: superadmin создан")
        else:
            print("SKIP: superadmin уже существует")
    finally:
        db.close()


if __name__ == "__main__":
    run()