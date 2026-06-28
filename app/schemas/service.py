from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from app.schemas.enums import ServiceCategory

class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: ServiceCategory
    subcategory: Optional[str] = None
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    duration_minutes: Optional[int] = Field(None, gt=0)
    max_capacity: Optional[int] = Field(1, ge=1)
    trainer_id: Optional[UUID] = None
    schedule: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None
    schedule: Optional[Dict[str, Any]] = None
    max_capacity: Optional[int] = None

class ServiceResponse(ServiceBase):
    id: UUID
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class ServiceBookingBase(BaseModel):
    client_id: UUID = Field(...)
    service_id: UUID = Field(...)
    booking_date: datetime

class ServiceBookingCreate(ServiceBookingBase):
    pass

class ServiceBookingResponse(ServiceBookingBase):
    id: UUID
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class ServiceAvailabilityResponse(BaseModel):
    service_id: int
    service_name: str
    date: date
    available_slots: List[Dict[str, Any]]
    is_available: bool