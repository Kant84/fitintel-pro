# app/schemas/locker_session.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import LockType, LockerSessionStatus


class LockerSessionResponse(BaseModel):
    """Ответ с информацией о сессии шкафчика"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    locker_id: UUID
    locker_number: str | None = None
    client_id: UUID
    client_name: str | None = None
    credential_id: UUID | None
    lock_type: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    info_terminal_id: str | None
    register_terminal_id: str | None
    created_at: datetime


class LockerSessionListResponse(BaseModel):
    """Список активных сессий"""
    
    items: list[LockerSessionResponse]
    count: int