from uuid import UUID
from pydantic import BaseModel


class PermissionRead(BaseModel):
    id: UUID
    code: str
    name: str
    module: str
    description: str | None = None

    model_config = {
        "from_attributes": True
    }