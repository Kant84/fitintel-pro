from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DynamicQRCreate(BaseModel):
    client_id: int = Field(..., gt=0)

class DynamicQRResponse(BaseModel):
    id: int
    client_id: int
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
    client_id: Optional[int]
    message: str
    access_granted: bool