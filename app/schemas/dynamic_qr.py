from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class DynamicQRCreate(BaseModel):
    client_id: UUID = Field(...)
    max_uses: int = Field(1, ge=1, description="Максимальное число использований")
    expires_in_minutes: int = Field(5, ge=1, le=1440, description="Время жизни QR в минутах (1-1440)")
    device_id: Optional[str] = Field(None, description="Привязка QR к устройству")

class DynamicQRResponse(BaseModel):
    id: UUID  # <-- Меняем int на UUID
    client_id: UUID
    qr_payload: str
    expires_at: datetime
    created_at: datetime
    class Config:
        from_attributes = True

class QRValidateRequest(BaseModel):
    qr_payload: str = Field(..., min_length=10)
    device_id: Optional[str] = None

class QRValidateResponse(BaseModel):
    valid: bool
    client_id: Optional[UUID]
    message: str
    access_granted: bool


class GuestQRCreate(BaseModel):
    email: str = Field(..., description="Email гостя")
    expires_in_minutes: int = Field(60, ge=1, le=1440)

class GroupQRCreate(BaseModel):
    client_ids: list = Field(..., description="Список UUID клиентов группы")
    expires_in_minutes: int = Field(60, ge=1, le=1440)
