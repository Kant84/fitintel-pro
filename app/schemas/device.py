# app/schemas/device.py
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class DeviceCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    type: str = Field(..., max_length=50)
    ip_address: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    code: str
    type: str
    ip_address: Optional[str]
    status: str
    last_ping_at: Optional[datetime]
    description: Optional[str]
    created_at: datetime

class DeviceListResponse(BaseModel):
    items: List[DeviceResponse]
    total: int
