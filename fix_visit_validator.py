# fix_visit_validator.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_validator = '''    @validator("client_id", always=True)
    def validate_identifier(cls, v, values):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if not v and not values.get("card_id") and not values.get("face_id") and not values.get("qr_payload"):
            raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return v'''

new_validator = '''    @validator("client_id", always=True)
    def validate_identifier(cls, v, values):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if not v and not values.get("card_id") and not values.get("face_id") and not values.get("qr_payload"):
            raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return v'''

# Валидатор уже корректный, но нужно сделать client_id необязательным
# Проверим, что client_id уже Optional
if "client_id: UUID | None = Field(default=None" in content:
    print("client_id уже Optional — OK")
else:
    print("ERROR: client_id не Optional")
