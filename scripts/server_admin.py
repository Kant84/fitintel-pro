"""Separate installer server-admin authentication and migration."""
import argparse
import getpass
import os
import sys
import uuid

from sqlalchemy import text

from app.core.security import get_password_hash, verify_password
from app.db.session import SessionLocal


class SafeError(Exception):
    pass


def _value(env_name, prompt, hidden=False):
    value = os.environ.get(env_name, "").strip()
    if not value and sys.stdin.isatty():
        value = (getpass.getpass(prompt) if hidden else input(prompt)).strip()
    if not value:
        raise SafeError(f"Required value is missing: {env_name}")
    return value


def _server_admin(db, username):
    return db.execute(text("""
        SELECT id, username, email, password_hash, is_active
        FROM server_admins
        WHERE lower(username) = lower(:username)
           OR lower(email) = lower(:username)
        LIMIT 1
    """), {"username": username}).mappings().first()


def create():
    username = _value("FITINTEL_ADMIN_USERNAME", "Server admin email: ")
    email = os.environ.get("FITINTEL_ADMIN_EMAIL", "").strip() or username
    password = _value("FITINTEL_ADMIN_PASSWORD", "Server admin password: ", True)
    if len(password) < 8:
        raise SafeError("Server admin password must contain at least 8 characters")

    db = SessionLocal()
    try:
        if _server_admin(db, username) or _server_admin(db, email):
            raise SafeError("Server admin already exists")
        db.execute(text("""
            INSERT INTO server_admins (
                id, username, email, password_hash,
                is_active, created_at, updated_at
            ) VALUES (
                :id, :username, :email, :password_hash,
                TRUE, now(), now()
            )
        """), {
            "id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "password_hash": get_password_hash(password),
        })
        db.commit()
        print("SERVER_ADMIN_CREATED=1")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def login():
    username = _value("FITINTEL_SERVER_ADMIN_USERNAME", "Server admin login: ")
    password = _value("FITINTEL_SERVER_ADMIN_PASSWORD", "Password: ", True)

    db = SessionLocal()
    try:
        admin = _server_admin(db, username)
        if not admin or not admin["is_active"] or not verify_password(
                password, admin["password_hash"]):
            raise SafeError("Server admin authentication failed")
        db.execute(text(
            "UPDATE server_admins SET last_login_at=now() WHERE id=:id"
        ), {"id": str(admin["id"])})
        db.commit()
        print("SERVER_ADMIN_AUTH_OK=1")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def migrate():
    username = _value("FITINTEL_INSTALLER_USERNAME", "Current installer login: ")
    password = _value("FITINTEL_INSTALLER_PASSWORD", "Current password: ", True)

    db = SessionLocal()
    try:
        user = db.execute(text("""
            SELECT id, username, email, password_hash, is_superuser
            FROM users
            WHERE (lower(username)=lower(:username)
                   OR lower(email)=lower(:username))
              AND deleted_at IS NULL
            LIMIT 1
        """), {"username": username}).mappings().first()

        if not user or not user["is_superuser"]:
            raise SafeError("Installer superuser account was not found")
        if not verify_password(password, user["password_hash"]):
            raise SafeError("Current installer password is incorrect")

        owner_logins = {
            str(row[0]).casefold()
            for row in db.execute(text(
                "SELECT superadmin_login FROM license_state WHERE id=1"
            )).fetchall()
        }
        user_logins = {
            str(user["username"] or "").casefold(),
            str(user["email"] or "").casefold(),
        }
        if owner_logins & user_logins:
            raise SafeError("Refusing to migrate the license owner")

        if _server_admin(db, user["username"]):
            raise SafeError("Server admin already exists; account was not changed")

        admin_id = str(uuid.uuid4())
        db.execute(text("""
            INSERT INTO server_admins (
                id, username, email, password_hash, is_active,
                migrated_from_user_id, created_at, updated_at
            ) VALUES (
                :id, :username, :email, :password_hash, TRUE,
                :source_id, now(), now()
            )
        """), {
            "id": admin_id,
            "username": user["username"],
            "email": user["email"] or user["username"],
            "password_hash": user["password_hash"],
            "source_id": str(user["id"]),
        })

        copied = db.execute(text(
            "SELECT password_hash FROM server_admins WHERE id=:id"
        ), {"id": admin_id}).first()
        if not copied or not verify_password(password, copied[0]):
            raise SafeError("New server admin verification failed; no user changed")

        uid = str(user["id"])
        tombstone = "deleted_" + uid.replace("-", "")[:8]

        # Проверка нового входа прошла. Старую club-учётную запись отключаем,
        # но сохраняем строку для исторических FK.
        db.execute(text("DELETE FROM user_roles WHERE user_id=:uid"), {"uid": uid})
        db.execute(text("""
            UPDATE users
            SET username=:tombstone,
                email=:email,
                password_hash=:random_hash,
                is_active=FALSE,
                is_superuser=FALSE,
                is_verified=FALSE,
                deleted_at=now(),
                updated_at=now()
            WHERE id=:uid
        """), {
            "uid": uid,
            "tombstone": tombstone,
            "email": tombstone + "@deleted.local",
            "random_hash": get_password_hash(uuid.uuid4().hex),
        })

        db.commit()
        print("SERVER_ADMIN_MIGRATED=1")
        print("SERVER_ADMIN_PASSWORD_VERIFIED=1")
        print("INSTALLER_CLUB_ACCOUNT_DISABLED=1")
        print("INSTALLER_HISTORY_TOMBSTONE=1")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("create")
    sub.add_parser("login")
    sub.add_parser("migrate")
    args = parser.parse_args()

    try:
        {"create": create, "login": login, "migrate": migrate}[args.command]()
    except SafeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"Server admin operation failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()