# app/schemas/locker.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import LockerType, LockerStatus, LockType


# ==========================================================
# ОСНОВНЫЕ СХЕМЫ
# ==========================================================

class LockerBase(BaseModel):
    """Базовые поля шкафчика"""
    
    number: str = Field(max_length=50, description="Номер шкафчика")
    zone: str | None = Field(None, max_length=100, description="Зона")
    lock_type: LockType = Field(default=LockType.OFFLINE, description="Тип замка")
    requires_privilege: bool = Field(default=False, description="Требуется привилегия")
    notes: str | None = Field(None, max_length=500, description="Заметки")


class LockerCreateRequest(LockerBase):
    """Создание шкафчика"""
    
    device_id: str | None = Field(None, max_length=255, description="ID устройства замка")


class LockerUpdateRequest(BaseModel):
    """Обновление шкафчика"""
    
    status: LockerStatus | None = Field(None, description="Статус")
    zone: str | None = Field(None, max_length=100, description="Зона")
    device_id: str | None = Field(None, max_length=255, description="ID устройства")
    requires_privilege: bool | None = Field(None, description="Требуется привилегия")
    notes: str | None = Field(None, max_length=500, description="Заметки")


class LockerResponse(LockerBase):
    """Ответ с информацией о шкафчике"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    device_id: str | None
    created_at: datetime
    updated_at: datetime


class LockerListResponse(BaseModel):
    """Список шкафчиков"""
    
    items: list[LockerResponse]
    count: int
    free_count: int = Field(description="Количество свободных шкафчиков")
    occupied_count: int = Field(description="Количество занятых")


# ==========================================================
# ДЛЯ КЛИЕНТОВ
# ==========================================================

class LockerAssignRequest(BaseModel):
    """Выбор шкафчика (ONLINE)"""
    
    locker_number: str = Field(description="Номер шкафчика")
    credential_value: str = Field(description="QR-код или UID метки")
    terminal_id: str = Field(description="ID инфотерминала")


class LockerInfoRequest(BaseModel):
    """Запрос номера шкафчика по браслету (OFFLINE)"""
    
    credential_value: str = Field(description="QR-код или UID метки")
    terminal_id: str = Field(description="ID инфотерминала")


class LockerInfoResponse(BaseModel):
    """Ответ с номером шкафчика"""
    
    has_locker: bool
    locker_number: str | None = None
    lock_type: str | None = None
    message: str | None = None


class LockerReleaseRequest(BaseModel):
    """Освобождение шкафчика (выход)"""
    
    credential_value: str = Field(description="QR-код или UID метки")