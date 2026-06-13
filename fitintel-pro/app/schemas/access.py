# app/schemas/access.py

from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field
from app.schemas.enums import AccessDecision


# ==========================================================
# ПРОВЕРКА ДОСТУПА
# ==========================================================

class AccessCheckRequest(BaseModel):
    """Схема запроса на проверку доступа"""
    
    credential: str = Field(
        min_length=1,
        max_length=255,
        description="QR-код или UID RFID-метки",
        examples=["qr_abc123", "rfid_1234567890"],
    )
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID турникета/терминала",
        examples=["turnstile_01", "terminal_entrance"],
    )
    zone: str | None = Field(
        default=None,
        max_length=100,
        description="Зона клуба",
        examples=["GYM", "POOL", "STUDIO"],
    ) 
    device_type: str | None = Field(
        default=None,
        description="Тип устройства (если неизвестен — игнорируется)",
    )

class AccessCheckResponse(BaseModel):
    """Схема ответа на проверку доступа"""
    
    decision: AccessDecision = Field(description="Решение: ALLOW или DENY")
    reason: str | None = Field(default=None, description="Причина решения")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    subscription_status: str | None = Field(default=None, description="Статус абонемента")
    visits_left: int | None = Field(default=None, description="Осталось посещений")
    subscription_end_date: date | None = Field(default=None, description="Дата окончания")


# ==========================================================
# ПРЕДОСТАВЛЕНИЕ ДОСТУПА
# ==========================================================

class AccessGrantRequest(BaseModel):
    """Схема запроса на предоставление доступа (вход)"""
    
    credential: str = Field(
        min_length=1,
        max_length=255,
        description="QR-код или UID RFID-метки",
    )
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID турникета/терминала",
    )
    zone: str | None = Field(default=None, max_length=100, description="Зона клуба")
    override: bool = Field(default=False, description="Принудительное открытие")
    override_by_user_id: UUID | None = Field(
        default=None,
        description="ID менеджера (при override)",
    )


class AccessGrantResponse(BaseModel):
    """Схема ответа на предоставление доступа"""
    
    granted: bool = Field(description="Доступ разрешён")
    reason: str | None = Field(default=None, description="Причина")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    visit_id: UUID | None = Field(default=None, description="ID созданного посещения")


# ==========================================================
# ВЫХОД
# ==========================================================

class AccessExitRequest(BaseModel):
    """Схема запроса на выход"""
    
    credential: str = Field(
        min_length=1,
        max_length=255,
        description="QR-код или UID RFID-метки",
    )
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID турникета/терминала",
    )

class AccessExitResponse(BaseModel):
    """Схема ответа на выход"""
    
    success: bool = Field(description="Успешно")
    reason: str | None = Field(default=None, description="Причина (если ошибка)")
    visit_id: UUID | None = Field(default=None, description="ID завершённого посещения")
    duration_minutes: int | None = Field(default=None, description="Длительность пребывания")