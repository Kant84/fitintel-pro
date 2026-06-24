# fix_visit_entry_schema.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_entry = '''class VisitEntryRequest(BaseModel):
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
        description="Зона",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Заметки",
    )
    entry_time: datetime | None = Field(
        default=None,
        description="Время входа (если не указано — текущее)",
    )
    subscription_id: UUID | None = Field(
        default=None,
        description="ID абонемента (если выбран конкретный)",
    )'''

new_entry = '''class VisitEntryRequest(BaseModel):
    """Схема запроса на вход"""
    
    # Идентификаторы клиента (минимум один должен быть указан)
    client_id: UUID | None = Field(default=None, description="ID клиента")
    card_id: str | None = Field(default=None, max_length=128, description="ID карты RFID")
    face_id: str | None = Field(default=None, max_length=255, description="ID Face ID шаблона")
    qr_payload: str | None = Field(default=None, max_length=512, description="QR-код payload")
    
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
        description="Зона",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Заметки",
    )
    entry_time: datetime | None = Field(
        default=None,
        description="Время входа (если не указано — текущее)",
    )
    subscription_id: UUID | None = Field(
        default=None,
        description="ID абонемента (если выбран конкретный)",
    )
    
    @validator("client_id", always=True)
    def validate_identifier(cls, v, values):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if not v and not values.get("card_id") and not values.get("face_id") and not values.get("qr_payload"):
            raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return v'''

if old_entry in content:
    content = content.replace(old_entry, new_entry)
    with open('app/schemas/visit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("VisitEntryRequest расширен — добавлены card_id, face_id, qr_payload!")
else:
    print("ERROR: Не найдена схема")
