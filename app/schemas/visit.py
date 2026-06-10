# app/schemas/visit.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import VisitStatus, AccessMethod


# ==========================================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================================

class VisitBase(BaseModel):
    """Базовые поля посещения"""
    
    client_id: UUID = Field(description="ID клиента")
    subscription_id: UUID | None = Field(
        default=None,
        description="ID абонемента (если есть)",
    )
    access_method: AccessMethod = Field(
        default=AccessMethod.QR,
        description="Способ доступа",
    )
    access_device_id: str | None = Field(
        default=None,
        max_length=255,
        description="ID устройства (турникет, терминал)",
    )
    zone: str | None = Field(
        default=None,
        max_length=100,
        description="Зона клуба (GYM, POOL, STUDIO, ENTRANCE)",
    )
    notes: str | None = Field(
        default=None,
        description="Заметки",
    )


# ==========================================================
# СХЕМЫ ДЛЯ ВХОДА/ВЫХОДА
# ==========================================================

class VisitEntryRequest(BaseModel):
    """Схема запроса на вход"""
    
    client_id: UUID = Field(description="ID клиента")
    access_method: AccessMethod = Field(
        default=AccessMethod.QR,
        description="Способ доступа",
    )
    access_device_id: str | None = Field(
        default=None,
        max_length=255,
        description="ID устройства",
    )
    zone: str | None = Field(
        default=None,
        max_length=100,
        description="Зона клуба",
    )
    entry_time: datetime | None = Field(
        default=None,
        description="Время входа (если не указано — текущее)",
    )
    subscription_id: UUID | None = Field(
        default=None,
        description="ID абонемента (если выбран конкретный)",
    )


class VisitExitRequest(BaseModel):
    """Схема запроса на выход"""
    
    visit_id: UUID = Field(description="ID посещения")
    exit_time: datetime | None = Field(
        default=None,
        description="Время выхода (если не указано — текущее)",
    )
    notes: str | None = Field(default=None, description="Заметки")


class VisitCompleteRequest(BaseModel):
    """Схема принудительного закрытия посещения"""
    
    visit_id: UUID = Field(description="ID посещения")
    exit_time: datetime | None = Field(
        default=None,
        description="Время выхода",
    )
    notes: str | None = Field(default=None, description="Причина закрытия")


# ==========================================================
# СХЕМЫ ОТВЕТА
# ==========================================================

class VisitResponse(VisitBase):
    """Полная схема ответа посещения"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="ID посещения")
    entry_time: datetime = Field(description="Время входа")
    exit_time: datetime | None = Field(default=None, description="Время выхода")
    duration_minutes: int | None = Field(default=None, description="Длительность в минутах")
    access_granted: bool = Field(default=True, description="Доступ разрешён")
    access_denied_reason: str | None = Field(default=None, description="Причина отказа")
    status: VisitStatus = Field(default=VisitStatus.ACTIVE, description="Статус")
    processed_by_user_id: UUID | None = Field(default=None, description="Кто обработал")
    created_at: datetime = Field(description="Дата создания")
    updated_at: datetime = Field(description="Дата обновления")


class VisitListResponse(BaseModel):
    """Схема ответа для списка посещений"""
    
    items: list[VisitResponse] = Field(description="Список посещений")
    count: int = Field(description="Количество посещений")
    total_duration_minutes: int | None = Field(
        default=None,
        description="Общая длительность (для статистики)",
    )


class ActiveVisitsResponse(BaseModel):
    """Схема ответа для активных посещений (клиенты в клубе)"""
    
    items: list[VisitResponse] = Field(description="Список активных посещений")
    count: int = Field(description="Количество клиентов в клубе")


# ==========================================================
# СХЕМЫ ДЛЯ РУЧНЫХ ОПЕРАЦИЙ
# ==========================================================

class ManualVisitRequest(BaseModel):
    """Схема ручного добавления посещения"""
    
    client_id: UUID = Field(description="ID клиента")
    entry_time: datetime = Field(description="Время входа")
    exit_time: datetime | None = Field(default=None, description="Время выхода")
    subscription_id: UUID | None = Field(default=None, description="ID абонемента")
    access_method: AccessMethod = Field(
        default=AccessMethod.MANUAL,
        description="Способ доступа",
    )
    zone: str | None = Field(default=None, max_length=100, description="Зона")
    notes: str | None = Field(default=None, description="Заметки")


class ManualVisitResponse(VisitResponse):
    """Схема ответа для ручного добавления"""
    
    processed_by_user_id: UUID = Field(description="Кто добавил")


# ==========================================================
# СХЕМЫ ДЛЯ СТАТИСТИКИ
# ==========================================================

class VisitStatsRequest(BaseModel):
    """Схема запроса статистики"""
    
    period: str = Field(
        default="day",
        description="Период: day, week, month, year",
        pattern="^(day|week|month|year)$",
    )
    start_date: datetime = Field(description="Дата начала")
    end_date: datetime | None = Field(default=None, description="Дата окончания")
    zone: str | None = Field(default=None, max_length=100, description="Зона")


class VisitStatsResponse(BaseModel):
    """Схема ответа статистики"""
    
    total_visits: int = Field(description="Всего посещений")
    unique_clients: int = Field(description="Уникальных клиентов")
    avg_duration_minutes: float | None = Field(default=None, description="Средняя длительность")
    peak_hours: dict[int, int] = Field(
        default_factory=dict,
        description="Часы пик (час → количество)",
    )
    visits_by_day: dict[str, int] = Field(
        default_factory=dict,
        description="Посещения по дням",
    )
    visits_by_zone: dict[str, int] | None = Field(
        default=None,
        description="Посещения по зонам",
    )


# ==========================================================
# СХЕМЫ ДЛЯ УДАЛЕНИЯ
# ==========================================================

class VisitDeleteRequest(BaseModel):
    """Схема запроса на отмену посещения"""
    
    reason: str = Field(
        min_length=1,
        max_length=255,
        description="Причина отмены",
    )
    notes: str | None = Field(default=None, description="Дополнительные заметки")