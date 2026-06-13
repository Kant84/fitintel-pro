# app/schemas/access_cache.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AccessCacheItem(BaseModel):
    """Элемент кэша для одного клиента"""
    
    credential_value: str = Field(description="QR-код или UID метки")
    access_granted: bool = Field(description="Доступ разрешён")
    client_name: str | None = Field(None, description="Имя клиента")
    subscription_status: str | None = Field(None, description="Статус абонемента")
    visits_left: int | None = Field(None, description="Осталось посещений")
    subscription_end_date: datetime | None = Field(None, description="Дата окончания")


class AccessCacheResponse(BaseModel):
    """Ответ с кэшем для устройства"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    credential_value: str
    access_granted: bool
    client_name: str | None
    subscription_status: str | None
    visits_left: int | None
    subscription_end_date: datetime | None
    valid_from: datetime
    valid_until: datetime
    cache_version: int
    device_id: str | None


class AccessCacheSyncRequest(BaseModel):
    """Запрос на синхронизацию кэша"""
    
    device_id: str = Field(description="ID устройства")
    last_cache_version: int = Field(default=0, description="Последняя версия кэша")


class AccessCacheSyncResponse(BaseModel):
    """Ответ на синхронизацию кэша"""
    
    need_update: bool = Field(description="Нужно обновить кэш")
    cache_version: int = Field(description="Новая версия кэша")
    items: list[AccessCacheItem] = Field(default_factory=list, description="Элементы кэша")