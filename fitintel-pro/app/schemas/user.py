# app/schemas/user.py

# импорт UUID для типизации идентификаторов
from uuid import UUID

# импорт BaseModel, ConfigDict и Field из Pydantic
from pydantic import BaseModel, ConfigDict, Field


# схема роли пользователя в ответе API
class UserRoleSchema(BaseModel):
    # разрешаем строить схему из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # код роли
    code: str

    # отображаемое имя роли
    name: str | None = None


# схема права пользователя в ответе API
class UserPermissionSchema(BaseModel):
    # разрешаем строить схему из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # код права
    code: str

    # отображаемое имя права
    name: str | None = None


# схема ответа по пользователю
class UserResponse(BaseModel):
    # разрешаем строить схему из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    # UUID пользователя
    id: UUID

    # email пользователя
    email: str | None = None

    # username пользователя
    username: str | None = None

    # активность пользователя
    is_active: bool = True

    # список ролей
    roles: list[UserRoleSchema] = []

    # список прав
    permissions: list[UserPermissionSchema] = []


# схема ответа для списка пользователей
class UserListResponse(BaseModel):
    # список элементов
    items: list[UserResponse]

    # количество элементов
    count: int


# схема запроса на создание пользователя
class UserCreateRequest(BaseModel):
    # email можно не передавать
    email: str | None = None

    # username можно не передавать, но обычно он нужен
    username: str | None = Field(default=None, min_length=3, max_length=100)

    # пароль обязателен при создании
    password: str = Field(min_length=6, max_length=128)

    # активен ли пользователь сразу после создания
    is_active: bool = True


# схема запроса на обновление пользователя
class UserUpdateRequest(BaseModel):
    # новый email
    email: str | None = None

    # новый username
    username: str | None = Field(default=None, min_length=3, max_length=100)

    # новый пароль
    #password: str | None = Field(default=None, min_length=6, max_length=128)

    # новый флаг активности
    is_active: bool | None = None


# схема запроса на назначение роли
class UserRoleAssignRequest(BaseModel):
    # код роли, например manager
    role_code: str = Field(min_length=1, max_length=100)


# схема запроса на снятие роли
class UserRoleRevokeRequest(BaseModel):
    # код роли, которую нужно снять
    role_code: str = Field(min_length=1, max_length=100)
    
class SelfUpdateRequest(BaseModel):
    email: str | None = None
    username: str | None = Field(default=None, min_length=3, max_length=100)   