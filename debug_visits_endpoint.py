# debug_visits_endpoint.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_checkin = '''    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
    if not has_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать client_id, card_id, face_id или qr_payload",
        )'''

new_checkin = '''    # DEBUG
    print(f"DEBUG payload: client_id={payload.client_id}, card_id={payload.card_id}, face_id={payload.face_id}, qr_payload={payload.qr_payload}")
    
    # Проверяем, что указан хотя бы один идентификатор
    has_id = any([
        payload.client_id,
        payload.card_id,
        payload.face_id,
        payload.qr_payload,
    ])
    print(f"DEBUG has_id={has_id}")
    if not has_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать client_id, card_id, face_id или qr_payload",
        )'''

if old_checkin in content:
    content = content.replace(old_checkin, new_checkin)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG добавлен в endpoint!")
else:
    print("ERROR: Не найден endpoint")
