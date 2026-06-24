# fix_visits_endpoint_validation.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_checkin = '''    service = VisitService(db)
    visit = service.entry(
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
    )
    return service._build_response(visit)'''

new_checkin = '''    # Проверяем, что указан хотя бы один идентификатор
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
        )
    
    service = VisitService(db)
    visit = service.entry(
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
    )
    return service._build_response(visit)'''

if old_checkin in content:
    content = content.replace(old_checkin, new_checkin)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Валидация добавлена в endpoint check_in!")
else:
    print("ERROR: Не найден endpoint check_in")
