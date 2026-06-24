# app/api/v1/auth.py

# импорт стандартного datetime для расчёта срока жизни токена в ответе
from datetime import datetime, timezone

# импорт APIRouter, Depends и HTTPException
from fastapi import APIRouter, Depends, HTTPException, status

# импорт Session для типизации SQLAlchemy-сессии
from sqlalchemy.orm import Session

from fastapi.security import OAuth2PasswordRequestForm

# импорт зависимостей API
from app.api.dependencies import (
    get_current_active_user,
    require_permission,
    require_permissions,
    require_roles,
)

# импорт времени жизни токена
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, decode_token

# импорт сессии БД
from app.db.session import get_db

# импорт схем auth
from app.schemas.auth import CurrentUserResponse, LoginRequest, RegisterRequest, TokenResponse, TokenCheckResponse

# импорт сервиса auth
from app.services.auth_service import AuthService


# создаём роутер auth
router = APIRouter(prefix="/auth", tags=["auth"])


# маршрут логина
# это минимальный технический endpoint для проверки auth utilities

# маршрут регистрации
@router.post("/register", response_model=TokenResponse)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Регистрация нового пользователя"""
    # создаём сервис аутентификации
    auth_service = AuthService(db)
    
    # проверяем, существует ли пользователь по логину
    existing = auth_service.get_user_by_login(payload.login)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # проверяем, существует ли пользователь по email
    if payload.email:
        existing_email = auth_service.get_user_by_email(payload.email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")
    
    # создаём пользователя с email
    user = auth_service.create_user(payload.login, payload.password, payload.email)
    
    # генерируем токены
    access_token = auth_service.create_user_access_token(user)
    refresh_token = auth_service.create_user_access_token(user)  # TODO: add refresh token method
    
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
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # проверяем логин и пароль
    user = auth_service.authenticate_user(payload.login, payload.password)

    # если пользователь не найден или пароль неверный, возвращаем 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    # если пользователь неактивен, возвращаем 403
    if not auth_service.is_user_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    # создаём access token
    access_token = auth_service.create_user_access_token(user)

    # возвращаем токен и срок его жизни
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# маршрут возвращает данные текущего пользователя
@router.get("/me", response_model=CurrentUserResponse)
def read_me(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # возвращаем безопасное представление пользователя
    return auth_service.build_current_user_response(current_user)


# маршрут для проверки payload токена
# полезен именно на этапе utilities и диагностики
@router.get("/token-check", response_model=TokenCheckResponse)
def token_check(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # формируем ответ
    return {
        "user": auth_service.build_current_user_response(current_user),
        "message": "Токен корректный",
    }


# маршрут проверки доступа по праву users.read
# это технический маршрут для проверки RBAC-логики
# маршрут проверки одного права users.read
@router.get("/permissions/users-read-single", response_model=CurrentUserResponse)
def check_users_read_single_permission(
    current_user=Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # возвращаем безопасное представление пользователя
    return auth_service.build_current_user_response(current_user)


# маршрут проверки сразу нескольких прав
@router.post("/permissions/users-create-and-read", response_model=CurrentUserResponse)
def check_users_create_and_read_permissions(
    current_user=Depends(require_permissions("users.read", "users.create")),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # возвращаем безопасное представление пользователя
    return auth_service.build_current_user_response(current_user)


# маршрут проверки роли admin или owner
@router.get("/roles/admin-or-owner", response_model=CurrentUserResponse)
def check_admin_or_owner_role(
    current_user=Depends(require_roles("admin", "owner")),
    db: Session = Depends(get_db),
):
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # возвращаем безопасное представление пользователя
    return auth_service.build_current_user_response(current_user)

# OAuth2-совместимый маршрут логина для Swagger Authorize





# маршрут настройки 2FA
@router.post("/2fa/setup")
def setup_2fa(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Настройка 2FA"""
    return {"message": "2FA настроена", "user_id": str(current_user.id)}


# маршрут проверки 2FA кода
@router.post("/2fa/verify")
def verify_2fa(
    code: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Проверка 2FA кода"""
    return {"message": "2FA код верный", "user_id": str(current_user.id)}



# маршрут настройки 2FA
@router.post("/2fa/setup")
def setup_2fa(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Настройка 2FA"""
    return {"message": "2FA настроена", "user_id": str(current_user.id)}


# маршрут проверки 2FA кода
@router.post("/2fa/verify")
def verify_2fa(
    code: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Проверка 2FA кода"""
    return {"message": "2FA код верный", "user_id": str(current_user.id)}


# маршрут восстановления пароля
@router.post("/forgot-password")
def forgot_password(
    email: str,
    db: Session = Depends(get_db),
):
    """Восстановление пароля"""
    return {"message": "Ссылка отправлена", "email": email}


# маршрут сброса пароля
@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    """Сброс пароля"""
    return {"message": "Пароль изменён", "token": token}


# маршрут подтверждения email
@router.get("/verify-email")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """Подтверждение email по токену"""
    return {"message": "Email подтверждён", "token": token}


# маршрут выхода
@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Выход пользователя"""
    return {"message": "Выход выполнен", "user_id": str(current_user.id)}


# маршрут обновления токена
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Обновление access token по refresh token"""
    # создаём сервис аутентификации
    auth_service = AuthService(db)
    
    # TODO: реализовать проверку refresh token
    # пока просто проверяем логин/пароль и выдаём новый токен
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
    
    # создаём новый access token
    access_token = auth_service.create_user_access_token(user)
    
    # возвращаем токен
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
    # создаём сервис аутентификации
    auth_service = AuthService(db)

    # в OAuth2PasswordRequestForm логин всегда лежит в username
    user = auth_service.authenticate_user(form_data.username, form_data.password)

    # если пользователь не найден или пароль неверный, возвращаем 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    # если пользователь неактивен, возвращаем 403
    if not auth_service.is_user_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    # создаём access token
    access_token = auth_service.create_user_access_token(user)

    # возвращаем токен и срок жизни
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


