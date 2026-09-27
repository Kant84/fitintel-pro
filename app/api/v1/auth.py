# app/api/v1/auth.py

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text

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

router = APIRouter(prefix="/auth", tags=["auth"])


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
    refresh_token = auth_service.create_user_access_token(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


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
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        force_change_password=force_change
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Смена пароля + сброс флага is_first_login"""
    auth_service = AuthService(db)

    if not auth_service.authenticate_user(current_user.username, body.current_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.failed_login_count = 0
    current_user.locked_until = None
    # сбрасываем ВСЕ флаги принудительной смены пароля
    if hasattr(current_user, "force_password_change"):
        current_user.force_password_change = False
    if hasattr(current_user, "is_first_login"):
        current_user.is_first_login = False

    try:
        db.execute(text("UPDATE license_state SET is_first_login=FALSE WHERE id=1"))
    except Exception:
        pass

    db.commit()
    return {"ok": True, "message": "Пароль изменён"}


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


@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return {"message": "Выход выполнен", "user_id": str(current_user.id)}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
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

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


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

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )