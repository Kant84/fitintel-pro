# add_face_confidence_schema.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем face_confidence в VisitEntryRequest
old_fields = '''    qr_payload: str | None = Field(default=None, max_length=512, description="QR-код payload")
    
    access_method: AccessMethod = Field('''

new_fields = '''    qr_payload: str | None = Field(default=None, max_length=512, description="QR-код payload")
    face_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Уверенность распознавания лица (0.0-1.0)",
    )
    
    access_method: AccessMethod = Field('''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/schemas/visit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("face_confidence добавлен в VisitEntryRequest!")
else:
    print("ERROR: Не найдены поля для вставки")
