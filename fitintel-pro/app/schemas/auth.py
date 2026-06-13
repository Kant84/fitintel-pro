# app/schemas/auth.py

# импорт UUID для типизации идентификатора пользователя
from uuid import UUID

# импорт BaseModel и Field из Pydantic
from pydantic import BaseModel, Field


# ============================================================
# ЛОГИН И ТОКЕНЫ
# ============================================================

# схема запроса на логин
class LoginRequest(BaseModel):
    # логин пользователя: username или email
    login: str

    # пароль пользователя
    password: str


# схема ответа с access token
class TokenResponse(BaseModel):
    # сам JWT access token
    access_token: str

    # тип токена
    token_type: str = "bearer"

    # срок жизни токена в секундах
    expires_in: int


# схема ответа с данными текущего пользователя
class CurrentUserResponse(BaseModel):
    # UUID пользователя
    id: UUID

    # email пользователя
    email: str | None = None

    # username пользователя
    username: str | None = None

    # активен ли пользователь
    is_active: bool

    # список кодов ролей
    roles: list[str] = []

    # список кодов прав
    permissions: list[str] = []


# схема ответа для проверки токена
class TokenCheckResponse(BaseModel):
    # пользователь из токена
    user: CurrentUserResponse

    # диагностическое сообщение
    message: str


# ============================================================
# SELF-SERVICE PASSWORD CHANGE
# ============================================================

# схема запроса на смену своего пароля
class ChangePasswordRequest(BaseModel):
    # текущий пароль пользователя
    current_password: str = Field(min_length=1, max_length=128)

    # новый пароль пользователя
    new_password: str = Field(min_length=6, max_length=128)


# ============================================================
# ADMIN PASSWORD RESET
# ============================================================

# схема административного сброса пароля
class AdminResetPasswordRequest(BaseModel):
    # новый пароль, который администратор задаёт пользователю
    new_password: str = Field(min_length=6, max_length=128)

    # нужно ли заставить пользователя сменить пароль при следующем входе
    force_password_change: bool = True