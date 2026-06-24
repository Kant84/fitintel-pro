# app/schemas/locker.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class LockerCreateRequest(BaseModel):
    """Схема создания шкафчика (E11.1)"""
    number: str = Field(min_length=1, max_length=50, description="Номер шкафчика")
    zone: str | None = Field(default=None, max_length=100, description="Зона")
    lock_type: str = Field(default="OFFLINE", max_length=50, description="Тип замка: OFFLINE, KERONG, HTTP, MODBUS")
    device_id: str | None = Field(default=None, max_length=255, description="ID устройства (для интеграции)")
    requires_privilege: bool = Field(default=False, description="Требуется ли привилегия")
    notes: str | None = Field(default=None, max_length=500, description="Примечания")


class LockerResponse(BaseModel):
    """Схема ответа шкафчика"""
    id: UUID
    number: str
    zone: str | None
    lock_type: str
    status: str
    device_id: str | None
    requires_privilege: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LockerListResponse(BaseModel):
    """Схема списка шкафчиков"""
    items: list[LockerResponse]
    count: int


class LockerAssignRequest(BaseModel):
    """Схема выдачи шкафчика (E11.4)"""
    client_id: UUID = Field(description="ID клиента")
    credential_id: UUID | None = Field(default=None, description="ID credential (ключ/браслет)")


class LockerReleaseRequest(BaseModel):
    """Схема освобождения шкафчика (E11.6)"""
    pass


class LockerBlockRequest(BaseModel):
    """Схема блокировки шкафчика (E11.8)"""
    reason: str = Field(min_length=1, max_length=500, description="Причина блокировки")


class LockerStatusResponse(BaseModel):
    """Схема статуса шкафчика (E11.9)"""
    id: UUID
    number: str
    status: str
    client_id: UUID | None = None
    client_name: str | None = None
    session_id: UUID | None = None
    lock_status: str | None = None


class LockerOpenResponse(BaseModel):
    """Схема открытия замка (E11.13)"""
    success: bool
    locker_id: UUID
    message: str
    lock_status: str | None = None
