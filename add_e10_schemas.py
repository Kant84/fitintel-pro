# add_e10_schemas.py
with open('app/schemas/credential.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_schemas = '''


# ==========================================================
# E10.1: СОЗДАНИЕ КАРТЫ (CARD)
# ==========================================================

class CardCreateRequest(BaseModel):
    """Схема создания карты доступа (E10.1)"""
    
    client_id: UUID = Field(description="ID клиента")
    card_number: str = Field(
        min_length=1,
        max_length=255,
        description="Номер карты (UID или магнитная полоса)",
        examples=["1234567890", "A1B2C3D4"],
    )
    valid_until: date | None = Field(
        default=None,
        description="Срок действия карты",
        examples=["2026-12-31"],
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Комментарий",
    )


# ==========================================================
# E10.3: СОЗДАНИЕ БРАСЛЕТА (BRACELET)
# ==========================================================

class BraceletCreateRequest(BaseModel):
    """Схема создания браслета (E10.3)"""
    
    client_id: UUID = Field(description="ID клиента")
    bracelet_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID браслета (RFID UID)",
        examples=["E200341502001080"],
    )
    rfid_manufacturer: str | None = Field(
        default=None,
        max_length=100,
        description="Производитель RFID",
        examples=["Kerong"],
    )
    rfid_model: str | None = Field(
        default=None,
        max_length=100,
        description="Модель RFID",
        examples=["KR-S50"],
    )
    valid_until: date | None = Field(
        default=None,
        description="Срок действия браслета",
        examples=["2026-12-31"],
    )


# ==========================================================
# E10.4: СОЗДАНИЕ МОБИЛЬНОГО КЛЮЧА (MOBILE_KEY)
# ==========================================================

class MobileKeyCreateRequest(BaseModel):
    """Схема создания мобильного ключа (E10.4)"""
    
    client_id: UUID = Field(description="ID клиента")
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="ID мобильного устройства",
        examples=["iphone_12_abc123"],
    )
    device_name: str | None = Field(
        default=None,
        max_length=255,
        description="Название устройства",
        examples=["iPhone 12 Андрея"],
    )
    valid_until: date | None = Field(
        default=None,
        description="Срок действия ключа",
        examples=["2026-12-31"],
    )


# ==========================================================
# E10.9: ПЕРЕПРИВЯЗКА КАРТЫ
# ==========================================================

class CredentialReassignRequest(BaseModel):
    """Схема перепривязки credential (E10.9)"""
    
    new_client_id: UUID = Field(description="ID нового клиента")


# ==========================================================
# E10.11: ВАЛИДАЦИЯ CREDENTIAL
# ==========================================================

class CredentialValidateResponse(BaseModel):
    """Схема ответа валидации (E10.11-12)"""
    
    valid: bool = Field(description="Валиден ли credential")
    credential_id: UUID | None = Field(default=None, description="ID credential")
    credential_type: str | None = Field(default=None, description="Тип credential")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    subscription_active: bool = Field(default=False, description="Активен ли абонемент")
    subscription_end_date: date | None = Field(default=None, description="Дата окончания абонемента")
    reason: str | None = Field(default=None, description="Причина если не валиден")


# ==========================================================
# E10.13: ЭМУЛЯЦИЯ КАРД-РИДЕРА
# ==========================================================

class CardReaderEmulateRequest(BaseModel):
    """Схема эмуляции кард-ридера (E10.13)"""
    
    card_data: str = Field(
        min_length=1,
        max_length=1024,
        description="Сырые данные с кард-ридера",
        examples=[";1234567890=1234?"],
    )
    format: str | None = Field(
        default="auto",
        description="Формат данных: auto, wiegand26, wiegand34, magstripe",
    )


class CardReaderEmulateResponse(BaseModel):
    """Схема ответа эмуляции (E10.13-14)"""
    
    success: bool = Field(description="Успешно ли распознана карта")
    card_number: str | None = Field(default=None, description="Извлечённый номер карты")
    credential_id: UUID | None = Field(default=None, description="ID credential")
    client_id: UUID | None = Field(default=None, description="ID клиента")
    client_name: str | None = Field(default=None, description="Имя клиента")
    credential_type: str | None = Field(default=None, description="Тип credential")
    reason: str | None = Field(default=None, description="Причина ошибки")


# ==========================================================
# E10.15: ПРОГРАММИРОВАНИЕ MIFARE
# ==========================================================

class MifareProgramRequest(BaseModel):
    """Схема программирования MIFARE карты (E10.15)"""
    
    sector: int = Field(
        ge=0,
        le=15,
        description="Номер сектора (0-15)",
        examples=[1],
    )
    key_a: str = Field(
        min_length=12,
        max_length=12,
        description="Ключ A (12 hex символов)",
        examples=["FFFFFFFFFFFF"],
    )
    data: str | None = Field(
        default=None,
        max_length=32,
        description="Данные для записи (16 байт в hex)",
        examples=["1234567890ABCDEF1234567890ABCDEF"],
    )
'''

content = content + new_schemas

with open('app/schemas/credential.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("E10 схемы добавлены!")
