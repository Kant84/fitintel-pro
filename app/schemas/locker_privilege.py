# app/schemas/locker_privilege.py

from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import LockerPrivilegeType


class LockerPrivilegeCreateRequest(BaseModel):
    """Назначение привилегии"""
    
    client_id: UUID = Field(description="ID клиента")
    locker_type: LockerPrivilegeType = Field(description="Тип: VIP, RENTAL")
    valid_until: date | None = Field(None, description="Дата окончания")
    notes: str | None = Field(None, max_length=500, description="Заметки")


class LockerPrivilegeResponse(BaseModel):
    """Ответ с информацией о привилегии"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    locker_type: str
    valid_from: date
    valid_until: date | None
    issued_by_user_id: UUID | None
    notes: str | None
    created_at: datetime


class LockerPrivilegeListResponse(BaseModel):
    """Список привилегий клиента"""
    
    items: list[LockerPrivilegeResponse]
    count: int