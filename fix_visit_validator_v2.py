# fix_visit_validator_v2.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_validator = '''    @validator("client_id", always=True)
    def validate_identifier(cls, v, values):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if not v and not values.get("card_id") and not values.get("face_id") and not values.get("qr_payload"):
            raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return v'''

new_validator = '''    @model_validator(mode='before')
    def validate_identifier(cls, data):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if isinstance(data, dict):
            client_id = data.get("client_id")
            card_id = data.get("card_id")
            face_id = data.get("face_id")
            qr_payload = data.get("qr_payload")
            if not client_id and not card_id and not face_id and not qr_payload:
                raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return data'''

if old_validator in content:
    content = content.replace(old_validator, new_validator)
    # Добавляем импорт model_validator если нет
    if 'from pydantic import' in content and 'model_validator' not in content:
        content = content.replace(
            'from pydantic import BaseModel, ConfigDict, Field, validator',
            'from pydantic import BaseModel, ConfigDict, Field, validator, model_validator'
        )
    with open('app/schemas/visit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Валидатор исправлен на model_validator!")
else:
    print("ERROR: Не найден валидатор")
