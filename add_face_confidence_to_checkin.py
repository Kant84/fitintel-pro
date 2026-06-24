# add_face_confidence_to_checkin.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = '''    visit = service.entry(
        client_id=str(payload.client_id) if payload.client_id else None,
        subscription_id=str(payload.subscription_id) if payload.subscription_id else None,
        access_method=payload.access_method,
        access_device_id=payload.access_device_id,
        zone=payload.zone,
        entry_time=payload.entry_time,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
        card_id=payload.card_id,
        face_id=payload.face_id,
        qr_payload=payload.qr_payload,
    )'''

new_call = '''    visit = service.entry(
        client_id=str(payload.client_id) if payload.client_id else None,
        subscription_id=str(payload.subscription_id) if payload.subscription_id else None,
        access_method=payload.access_method,
        access_device_id=payload.access_device_id,
        zone=payload.zone,
        entry_time=payload.entry_time,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
        card_id=payload.card_id,
        face_id=payload.face_id,
        qr_payload=payload.qr_payload,
        face_confidence=payload.face_confidence,
    )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("face_confidence добавлен в check_in!")
else:
    print("ERROR: Не найден вызов service.entry")
