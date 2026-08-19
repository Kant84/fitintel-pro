from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class FaceRegisterRequest(BaseModel):
    client_id: UUID
    photo: str = Field(..., description="Фото в base64")

class FaceVerifyRequest(BaseModel):
    photo: str = Field(..., description="Фото в base64")

class FaceUpdateRequest(BaseModel):
    photo: str = Field(..., description="Новое фото в base64")

class FaceTurnstileRequest(BaseModel):
    photo: str
    device_id: str
    zone: Optional[str] = None
