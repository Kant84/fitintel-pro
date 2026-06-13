# app/schemas/credential.py

from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.enums import CredentialType, CredentialStatus


# ==========================================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================================

class CredentialBase(BaseModel):
    """Базовые поля учётных данных"""
    
    client_id: UUID = Field(description="ID клиента")
    credential_type: CredentialType = Field(description="Тип: QR, RFID")
    credential_value: str = Field(max_length=255, description="QR-код или UID метки")
    status: CredentialStatus = Field(default=CredentialStatus.ACTIVE, description="Статус")
    valid_from: date = Field(default_factory=date.today, description="Дата начала")
    valid_until: date | None = Field(None, description="Дата окончания")
    notes: str | None = Field(None, max_length=500, description="Заметки")


# ==========================================================
# ДЛЯ QR-КОДОВ
# ==========================================================

class QRCreateRequest(BaseModel):
    """Создание QR-кода для клиента"""
    
    client_id: UUID = Field(description="ID клиента")
    valid_until: date | None = Field(None, description="Дата окончания (опционально)")


class QRResponse(BaseModel):
    """Ответ с QR-кодом"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    credential_value: str = Field(description="QR-код (строка)")
    qr_image: str | None = Field(None, description="QR-код в формате base64 или URL")
    valid_from: date
    valid_until: date | None
    created_at: datetime


# ==========================================================
# ДЛЯ RFID-МЕТОК
# ==========================================================

class RFIDCreateRequest(BaseModel):
    """Привязка RFID-метки к клиенту"""
    
    client_id: UUID = Field(description="ID клиента")
    credential_value: str = Field(max_length=255, description="UID RFID-метки")
    rfid_manufacturer: str | None = Field(None, max_length=100, description="Производитель")
    rfid_model: str | None = Field(None, max_length=100, description="Модель")
    valid_until: date | None = Field(None, description="Дата окончания")


class RFIDResponse(BaseModel):
    """Ответ с информацией о RFID-метке"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    credential_value: str
    credential_type: str
    status: str
    valid_from: date
    valid_until: date | None
    rfid_manufacturer: str | None
    rfid_model: str | None
    created_at: datetime


# ==========================================================
# ОБЩИЕ СХЕМЫ
# ==========================================================

class CredentialResponse(BaseModel):
    """Полная схема ответа"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    client_id: UUID
    credential_type: str
    credential_value: str
    status: str
    valid_from: date
    valid_until: date | None
    qr_version: str | None
    qr_format: str | None
    rfid_manufacturer: str | None
    rfid_model: str | None
    issued_by_user_id: UUID | None
    issued_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CredentialListResponse(BaseModel):
    """Список учётных данных"""
    
    items: list[CredentialResponse]
    count: int


class CredentialBlockRequest(BaseModel):
    """Запрос на блокировку учётных данных"""
    
    reason: str = Field(min_length=1, max_length=255, description="Причина блокировки")