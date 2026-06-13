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
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse, TokenCheckResponse

# импорт сервиса auth
from app.services.auth_service import AuthService


# создаём роутер auth
router = APIRouter(prefix="/auth", tags=["auth"])


# маршрут логина
# это минимальный технический endpoint для проверки auth utilities
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