from uuid import UUID
from pydantic import BaseModel, Field, EmailStr

class LoginRequest(BaseModel):
    login: str
    password: str = Field(min_length=8, max_length=128)

class RegisterRequest(BaseModel):
    login: str
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    phone: str | None = None
    full_name: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    force_change_password: bool = False

class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr | None = None
    username: str | None = None
    is_active: bool
    roles: list[str] = []
    permissions: list[str] = []

class TokenCheckResponse(BaseModel):
    user: CurrentUserResponse
    message: str

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)

class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)
    force_password_change: bool = True