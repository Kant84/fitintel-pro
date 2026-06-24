# app/schemas/feature_flag.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum

class FlagScope(str, Enum):
    SYSTEM = "system"
    MODULE = "module"
    TENANT = "tenant"
    USER = "user"
    CANARY = "canary"

class FlagType(str, Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    JSON = "json"

class FlagConditions(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Дата начала действия флага")
    end_date: Optional[datetime] = Field(None, description="Дата окончания действия флага")
    percentage_rollout: Optional[int] = Field(None, ge=0, le=100, description="Процент раската (0-100)")
    allowed_roles: Optional[List[str]] = Field(None, description="Разрешённые роли")
    min_desktop_version: Optional[str] = Field(None, description="Минимальная версия десктопа")
    required_flags: Optional[List[str]] = Field(None, description="Флаги-зависимости")

    class Config:
        json_schema_extra = {
            "example": {
                "percentage_rollout": 50,
                "allowed_roles": ["SUPER_ADMIN", "ADMIN"],
                "min_desktop_version": "1.3.0",
                "required_flags": ["ACCESS_CONTROL"]
            }
        }

class FeatureFlagBase(BaseModel):
    flag_key: str = Field(..., min_length=1, max_length=128, description="Уникальный ключ флага. Пример: MODULE_FACE_ID")
    name: str = Field(..., min_length=1, max_length=255, description="Человекочитаемое название")
    description: Optional[str] = Field(None, description="Описание назначения флага")
    flag_type: FlagType = Field(default=FlagType.BOOLEAN, description="Тип значения флага")
    default_value: Any = Field(default=False, description="Значение по умолчанию (fallback)")
    target_value: Optional[Any] = Field(None, description="Целевое значение флага")
    scope: FlagScope = Field(default=FlagScope.SYSTEM, description="Уровень флага")
    target_id: Optional[int] = Field(None, description="ID цели (tenant/user) для не-системных флагов")
    conditions: Optional[FlagConditions] = Field(None, description="Условия активации")
    is_active: bool = Field(default=True, description="Активен ли флаг")

    @validator("flag_key")
    def validate_flag_key(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Ключ флага должен содержать только буквы, цифры, _ и -")
        return v

    @validator("target_value", pre=True)
    def validate_target_value(cls, v, values):
        flag_type = values.get("flag_type")
        if flag_type == FlagType.BOOLEAN and v is not None:
            if isinstance(v, str):
                v = v.lower() in ("true", "1", "yes", "on")
            elif not isinstance(v, bool):
                raise ValueError("Для boolean-флага target_value должно быть true/false")
        if flag_type == FlagType.INTEGER and v is not None:
            if isinstance(v, str):
                try:
                    v = int(v)
                except ValueError:
                    raise ValueError("Для integer-флага target_value должно быть числом")
            elif not isinstance(v, int):
                raise ValueError("Для integer-флага target_value должно быть числом")
        return v

class FeatureFlagCreate(FeatureFlagBase):
    pass

class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    target_value: Optional[Any] = None
    conditions: Optional[FlagConditions] = None
    is_active: Optional[bool] = None
    changed_by: Optional[str] = Field(None, description="Кто изменил флаг")

class FeatureFlagResponse(FeatureFlagBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    changed_by: Optional[str]

    class Config:
        from_attributes = True

class FeatureFlagCheckRequest(BaseModel):
    flag_key: str = Field(..., description="Ключ флага для проверки")
    tenant_id: Optional[int] = Field(None, description="ID клуба (для клиентских флагов)")
    user_id: Optional[int] = Field(None, description="ID пользователя (для пользовательских флагов)")
    user_role: Optional[str] = Field(None, description="Роль пользователя")
    desktop_version: Optional[str] = Field(None, description="Версия десктопа")

class FeatureFlagCheckResponse(BaseModel):
    flag_key: str
    value: Any
    source: str = Field(..., description="Откуда взято значение: default, system, module, tenant, user, canary")
    is_active: bool
    latency_ms: float = Field(..., description="Время проверки в мс")

class FeatureFlagBulkUpdate(BaseModel):
    flags: List[Dict[str, Any]] = Field(..., description="Список флагов для массового обновления")
    changed_by: str = Field(..., description="Кто выполняет изменение")

class FeatureFlagAuditResponse(BaseModel):
    id: int
    flag_id: int
    action: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    changed_by: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True