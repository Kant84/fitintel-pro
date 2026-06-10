# app/schemas/access_log.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import AccessDecision, AccessMode


class AccessLogEntry(BaseModel):
    """Запись журнала доступа"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    device_id: str
    credential_value: str
    credential_type: str | None
    client_id: UUID | None
    decision: str
    reason: str | None
    mode: str
    cache_used: bool
    created_at: datetime


class AccessLogListResponse(BaseModel):
    """Список записей журнала"""
    
    items: list[AccessLogEntry]
    count: int


class OfflineLogSyncRequest(BaseModel):
    """Синхронизация офлайн-журнала с терминала"""
    
    device_id: str = Field(description="ID устройства")
    logs: list[dict] = Field(description="Список записей с терминала")