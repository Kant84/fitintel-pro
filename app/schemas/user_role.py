from uuid import UUID

from pydantic import BaseModel


class UserRoleCreate(BaseModel):
    role_id: UUID


class UserRoleActionResult(BaseModel):
    status: str
    user_id: UUID
    role_id: UUID