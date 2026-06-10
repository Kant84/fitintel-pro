# app/schemas/role.py

from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from app.schemas.permission import PermissionRead


class RoleRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionRead] = []

    model_config = {
        "from_attributes": True
    }


class RoleUpdate(BaseModel):
    # Новый код роли
    code: Optional[str] = None

    # Новое имя роли
    name: Optional[str] = None

    # Новое описание роли
    description: Optional[str] = None

    # Новый признак системной роли
    is_system: Optional[bool] = None