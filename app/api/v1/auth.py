# app/api/v1/auth.py
"""
Аутентификация: register/login/me/change-password + настоящий refresh-flow.
Access-токен: короткий (ACCESS_TOKEN_EXPIRE_MINUTES, по умолчанию 30 мин).
Refresh-токен: длинный (REFRESH_TOKEN_EXPIRE_DAYS, по умолчанию 30 дней),
хранится в БД (хэш), ротируется на каждом /auth/refresh, отзывается на /logout.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_active_user,
    require_permission,
    require_permissions,
    require_roles,
)
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, decode_token, get_password_hash
from app.db.session import get_db
from app.schemas.auth import (
    CurrentUserResponse, LoginRequest, RegisterRequest,
    TokenResponse, TokenCheckResponse, ChangePasswordRequest
)
from app.services.auth_service import AuthService

try:
    from app.core.config import settings as _settings
    REFRESH_TOKEN_EXPIRE_DAYS = int(getattr(_settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30))
except Exception:
    REFRESH_TOKEN_EXPIRE_DAYS = 30

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------- DDL
_DDL_DONE = False


def _ensure(db: Session):
    """Таблица refresh-токенов (лениво, миграции не нужны)."""
    global _DDL_DONE
    if _DDL_DONE:
        return
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            token_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))
    db.commit()
    _DDL_DONE = True


def _hash(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def _issue_refresh_token(db: Session, user_id) -> str:
    """Создаёт refresh-токен, возвращает сырое значение (одноразово показывается клиенту)."""
    raw = secrets.token_urlsafe(48)
    db.execute(text(
        "INSERT INTO auth_refresh_tokens (id, user_id, token_hash, expires_at)"
        " VALUES (:i, :u, :h, :e)"),
        {"i": str(uuid.uuid4()), "u": str(user_id), "h": _hash(raw),
         "e": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)})
    db.commit()
    return raw


def _revoke_user_tokens(db: Session, user_id):
    db.execute(text(
        "UPDATE auth_refresh_tokens SET revoked = TRUE WHERE user_id = :u"),
        {"u": str(user_id)})
    db.commit()


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------- register
@router.post("/register", response_model=TokenResponse)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    existing = auth_service.get_user_by_login(payload.login)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    if payload.email:
        existing_email = auth_service.get_user_by_email(payload.email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")

    user = auth_service.create_user(payload.login, payload.password, payload.email)

    if getattr(payload, "phone", None):
        user.phone = payload.phone
        db.commit()

    access_token = auth_service.create_user_access_token(user)
    refresh_token = _issue_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# ---------------------------------------------------------------- login
@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(payload.login, payload.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not auth_service.is_user_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    access_token = auth_service.create_user_access_token(user)
    refresh_token = _issue_refresh_token(db, user.id)

    # === Проверка: первый вход SuperAdmin ===
    force_change = False
    if payload.login.lower() == "superadmin":
        try:
            row = db.execute(text("SELECT is_first_login FROM license_state WHERE id=1")).first()
            if row is None or row[0] is True or row[0] is None:
                force_change = True
        except Exception:
            force_change = True
    # ========================================

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        force_change_password=force_change
    )


# ---------------------------------------------------------------- change-password
@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Смена пароля + сброс флага is_first_login"""
    auth_service = AuthService(db)

    try:
        pwd_ok = auth_service.authenticate_user(current_user.username, body.current_password)
    except HTTPException:
        pwd_ok = None          # неверный текущий пароль ≠ 401 на смене пароля
    if not pwd_ok:
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.failed_login_count = 0
    current_user.locked_until = None
    if hasattr(current_user, "force_password_change"):
        current_user.force_password_change = False
    if hasattr(current_user, "is_first_login"):
        current_user.is_first_login = False

    try:
        db.execute(text(
            "INSERT INTO license_state (id, is_first_login, updated_at) "
            "VALUES (1, FALSE, now()) "
            "ON CONFLICT (id) DO UPDATE SET is_first_login = FALSE, updated_at = now()"
        ))
    except Exception:
        try:
            db.execute(text(
                "UPDATE license_state SET is_first_login = FALSE, updated_at = now() WHERE id = 1"
            ))
        except Exception:
            pass

    db.commit()
    _revoke_user_tokens(db, current_user.id)   # смена пароля = все сеансы завершены
    return {"ok": True, "message": "Пароль изменён"}

# ---------------------------------------------------------------- me / checks
@router.get("/me", response_model=CurrentUserResponse)
def read_me(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.build_current_user_response(current_user)


@router.get("/token-check", response_model=TokenCheckResponse)
def token_check(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return {
        "user": auth_service.build_current_user_response(current_user),
        "message": "Токен корректный",
    }


@router.get("/permissions/users-read-single", response_model=CurrentUserResponse)
def check_users_read_single_permission(
    current_user=Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.build_current_user_response(current_user)


@router.post("/permissions/users-create-and-read", response_model=CurrentUserResponse)
def check_users_create_and_read_permissions(
    current_user=Depends(require_permissions("users.read", "users.create")),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.build_current_user_response(current_user)


@router.get("/roles/admin-or-owner", response_model=CurrentUserResponse)
def check_admin_or_owner_role(
    current_user=Depends(require_roles("admin", "owner")),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.build_current_user_response(current_user)


# ---------------------------------------------------------------- заглушки 2FA/восстановления
@router.post("/2fa/setup")
def setup_2fa(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return {"message": "2FA настроена", "user_id": str(current_user.id)}


@router.post("/2fa/verify")
def verify_2fa(
    code: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return {"message": "2FA код верный", "user_id": str(current_user.id)}


@router.post("/forgot-password")
def forgot_password(
    email: str,
    db: Session = Depends(get_db),
):
    return {"message": "Ссылка отправлена", "email": email}


@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    return {"message": "Пароль изменён", "token": token}


@router.get("/verify-email")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    return {"message": "Email подтверждён", "token": token}


# ---------------------------------------------------------------- logout
@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _ensure(db)
    _revoke_user_tokens(db, current_user.id)
    return {"message": "Выход выполнен", "user_id": str(current_user.id)}


# ---------------------------------------------------------------- refresh (настоящий)
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Обмен refresh-токена на новую пару access+refresh (ротация).
    Старый refresh немедленно аннулируется — повторное использование невозможно."""
    _ensure(db)
    row = db.execute(text(
        "SELECT id, user_id, expires_at, revoked FROM auth_refresh_tokens"
        " WHERE token_hash = :h"), {"h": _hash(payload.refresh_token)}).first()
    if not row:
        raise HTTPException(status_code=401, detail="Невалидный refresh-токен")
    _id, user_id, expires_at, revoked = row
    now = datetime.now(timezone.utc)
    if isinstance(expires_at, str):            # SQLite/некоторые драйверы отдают строку
        expires_at = datetime.fromisoformat(expires_at)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if revoked or exp < now:
        raise HTTPException(status_code=401, detail="Refresh-токен истёк или отозван")

    # ротация: старый сгорает
    db.execute(text("UPDATE auth_refresh_tokens SET revoked = TRUE WHERE id = :i"),
               {"i": _id})
    db.commit()

    from app.models.user import User
    user = db.get(User, user_id)
    if user is None or not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Пользователь неактивен")

    auth_service = AuthService(db)
    access_token = auth_service.create_user_access_token(user)
    new_refresh = _issue_refresh_token(db, user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------- swagger login
@router.post("/token", response_model=TokenResponse)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not auth_service.is_user_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    access_token = auth_service.create_user_access_token(user)
    refresh_token = _issue_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )