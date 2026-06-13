# app/core/security.py

# импорт стандартного модуля os
# он нужен для чтения переменных окружения
import os

# импорт классов для работы с датой, временем и часовым поясом UTC
from datetime import datetime, timedelta, timezone

# импорт типа Any для словаря с дополнительными данными токена
from typing import Any

# импорт FastAPI-классов для возврата ошибок авторизации
from fastapi import HTTPException, status

# импорт схемы OAuth2 для чтения Bearer-токена из заголовка Authorization
from fastapi.security import OAuth2PasswordBearer

# импорт контекста для безопасного хеширования паролей
from passlib.context import CryptContext

# импорт библиотеки JWT
import jwt

# импорт исключений JWT
from jwt import ExpiredSignatureError, InvalidTokenError


# секретный ключ для подписи JWT
# сначала пробуем взять его из переменной окружения
# если переменной нет, используем безопасное значение по умолчанию только для локальной разработки
SECRET_KEY = os.getenv("FITNEXUS_SECRET_KEY", "fitnexus-dev-secret-key-change-me")


# алгоритм подписи JWT
# для текущего этапа достаточно HS256
ALGORITHM = os.getenv("FITNEXUS_SECURITY_ALGORITHM", "HS256")


# время жизни access token в минутах
# значение читается из переменной окружения
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("FITNEXUS_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)


# объект passlib для хеширования и проверки паролей
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)


# схема получения Bearer-токена из заголовка Authorization
# tokenUrl указывает маршрут входа
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# функция создаёт хеш пароля
def get_password_hash(password: str) -> str:
    # возвращаем готовый безопасный хеш
    return pwd_context.hash(password)


# функция проверяет, совпадает ли обычный пароль с хешем
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # возвращаем True, если пароль совпадает
    # иначе возвращаем False
    return pwd_context.verify(plain_password, hashed_password)


# функция создаёт JWT access token
def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_data: dict[str, Any] | None = None,
) -> str:
    # вычисляем срок жизни токена
    # если expires_delta передан, используем его
    # иначе берём стандартное время жизни из настроек
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # формируем payload токена
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "token_type": "access",
    }

    # если переданы дополнительные данные, добавляем их в payload
    if extra_data:
        payload.update(extra_data)

    # кодируем JWT и возвращаем готовую строку токена
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# функция декодирует JWT-токен
def decode_token(token: str) -> dict[str, Any]:
    try:
        # декодируем токен
        # одновременно проверяется подпись и срок действия
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        # возвращаем содержимое токена
        return payload

    except ExpiredSignatureError:
        # если токен просрочен, возвращаем ошибку 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истёк",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except InvalidTokenError:
        # если токен неверный, повреждённый или подписан другим ключом
        # возвращаем ошибку 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )