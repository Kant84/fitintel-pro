# fix_model_validator_null.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_validator = '''    @model_validator(mode='before')
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

new_validator = '''    @model_validator(mode='before')
    def validate_identifier(cls, data):
        """Проверяем, что указан хотя бы один идентификатор клиента"""
        if isinstance(data, dict):
            client_id = data.get("client_id")
            card_id = data.get("card_id")
            face_id = data.get("face_id")
            qr_payload = data.get("qr_payload")
            # Проверяем, что хотя бы один идентификатор указан и не пустой/null
            has_id = any([
                client_id and str(client_id).lower() not in ('null', 'none', ''),
                card_id and str(card_id).lower() not in ('null', 'none', ''),
                face_id and str(face_id).lower() not in ('null', 'none', ''),
                qr_payload and str(qr_payload).lower() not in ('null', 'none', ''),
            ])
            if not has_id:
                raise ValueError("Необходимо указать client_id, card_id, face_id или qr_payload")
        return data'''

if old_validator in content:
    content = content.replace(old_validator, new_validator)
    with open('app/schemas/visit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Валидатор исправлен — проверка на null!")
else:
    print("ERROR: Не найден валидатор")
