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


# ==========================================================
# E9.1-3: ОТКРЫТИЕ ПО КАРТЕ / QR
# ==========================================================

class AccessOpenRequest(BaseModel):
    """Схема запроса на открытие турникета (E9.1-3)"""
    
    credential: str = Field(
        min_length=1,
        max_length=255,
        description="QR-код или UID RFID-метки",
        examples=["qr_abc123", "rfid_1234567890"],
    )
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID турникета/считывателя",
        examples=["turnstile_01", "reader_gym"],
    )
    zone: str | None = Field(
        default=None,
        max_length=100,
        description="Зона: GYM, POOL, STUDIO, LOCKER, SPA, SOLARIUM",
        examples=["GYM"],
    )


class AccessOpenResponse(BaseModel):
    """Схема ответа на открытие турникета (E9.1-3)"""
    
    granted: bool = Field(description="Доступ разрешён")
    reason: str | None = Field(default=None, description="Причина (если отказ)")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    visit_id: UUID | None = Field(default=None, description="ID посещения")
    turnstile_open: bool = Field(default=False, description="Турникет открыт")
    device_id: str | None = Field(default=None, description="ID устройства")
    zone: str | None = Field(default=None, description="Зона")


# ==========================================================
# E9.4-5: РУЧНОЕ ОТКРЫТИЕ (ADMIN)
# ==========================================================

class AccessManualOpenRequest(BaseModel):
    """Схема запроса на ручное открытие (E9.4-5)"""
    
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID турникета/считывателя",
    )
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Причина ручного открытия",
        examples=["Клиент забыл карту", "Техническое обслуживание"],
    )


class AccessManualOpenResponse(BaseModel):
    """Схема ответа на ручное открытие (E9.4-5)"""
    
    success: bool = Field(description="Успешно")
    reason: str | None = Field(default=None, description="Причина (если ошибка)")
    device_id: str = Field(description="ID устройства")
    opened_by: UUID | None = Field(default=None, description="Кто открыл")
    audit_log_id: UUID | None = Field(default=None, description="ID записи в audit")


# ==========================================================
# E9.6: СТАТУС УСТРОЙСТВ
# ==========================================================

class DeviceStatus(BaseModel):
    """Статус одного устройства"""
    
    device_id: str = Field(description="ID устройства")
    name: str = Field(description="Название")
    device_type: str = Field(description="Тип")
    zone: str | None = Field(default=None, description="Зона")
    online: bool = Field(description="Онлайн")
    blocked: bool = Field(default=False, description="Заблокирован")
    anti_passback: bool = Field(default=False, description="Anti-passback включён")
    last_heartbeat: str | None = Field(default=None, description="Последний heartbeat")


class AccessStatusResponse(BaseModel):
    """Схема ответа со статусом устройств (E9.6)"""
    
    devices: list[DeviceStatus] = Field(default=[], description="Список устройств")
    total: int = Field(description="Всего устройств")
    online: int = Field(description="Онлайн")
    offline: int = Field(description="Офлайн")
    blocked: int = Field(default=0, description="Заблокировано")


# ==========================================================
# E9.7-8: БЛОКИРОВКА / РАЗБЛОКИРОВКА
# ==========================================================

class AccessBlockRequest(BaseModel):
    """Схема запроса на блокировку устройства (E9.7-8)"""
    
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Причина блокировки",
        examples=["Техническое обслуживание", "Поломка"],
    )


class AccessBlockResponse(BaseModel):
    """Схема ответа на блокировку/разблокировку (E9.7-8)"""
    
    success: bool = Field(description="Успешно")
    device_id: str = Field(description="ID устройства")
    blocked: bool = Field(description="Текущий статус блокировки")
    reason: str | None = Field(default=None, description="Причина")
    blocked_by: UUID | None = Field(default=None, description="Кто заблокировал")


# ==========================================================
# E9.9: ЛОГИ ДОСТУПА
# ==========================================================

class AccessLogEntry(BaseModel):
    """Одна запись в логе доступа"""
    
    id: UUID = Field(description="ID записи")
    timestamp: str = Field(description="Время события")
    event_type: str = Field(description="Тип: ENTRY, EXIT, BLOCKED, MANUAL_OPEN, EMERGENCY")
    credential: str | None = Field(default=None, description="Credential")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    device_id: str = Field(description="ID устройства")
    zone: str | None = Field(default=None, description="Зона")
    granted: bool = Field(description="Доступ разрешён")
    reason: str | None = Field(default=None, description="Причина")


class AccessLogResponse(BaseModel):
    """Схема ответа с логами доступа (E9.9)"""
    
    logs: list[AccessLogEntry] = Field(default=[], description="Список записей")
    total: int = Field(description="Всего записей")
    date_from: str | None = Field(default=None, description="Начало периода")
    date_to: str | None = Field(default=None, description="Конец периода")


# ==========================================================
# E9.13-14: ЭКСТРЕННОЕ ОТКРЫТИЕ
# ==========================================================

class AccessEmergencyUnlockResponse(BaseModel):
    """Схема ответа на экстренное открытие (E9.13-14)"""
    
    success: bool = Field(description="Успешно")
    unlocked_count: int = Field(description="Количество открытых устройств")
    unlocked_devices: list[str] = Field(default=[], description="Список открытых устройств")
    unlocked_by: UUID | None = Field(default=None, description="Кто открыл")
    audit_log_id: UUID | None = Field(default=None, description="ID записи в audit")
    message: str = Field(description="Сообщение")
