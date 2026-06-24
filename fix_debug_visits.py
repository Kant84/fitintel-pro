# fix_debug_visits.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_debug = '''    # DEBUG
    print(f"DEBUG payload: client_id={payload.client_id}, card_id={payload.card_id}, face_id={payload.face_id}, qr_payload={payload.qr_payload}")
    
    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
    print(f"DEBUG has_id={has_id}")'''

new_debug = '''    # DEBUG
    print(f"DEBUG payload type: {type(payload)}")
    print(f"DEBUG payload dict: {payload.model_dump()}")
    print(f"DEBUG face_id repr: {repr(payload.face_id)}")
    print(f"DEBUG face_id is None: {payload.face_id is None}")
    print(f"DEBUG face_id == '': {payload.face_id == ''}")
    
    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
    print(f"DEBUG has_id={has_id}")'''

if old_debug in content:
    content = content.replace(old_debug, new_debug)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG обновлён!")
else:
    print("ERROR: Не найден DEBUG")
