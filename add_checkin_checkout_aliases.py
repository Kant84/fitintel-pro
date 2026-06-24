# add_checkin_checkout_aliases.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим конец функции exit и добавляем алиасы после неё
old_exit = '''    return service._build_response(visit)


@router.post(
    "/{visit_id}/complete",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)'''

new_exit = '''    return service._build_response(visit)


# ==========================================================
# АЛИАСЫ ДЛЯ ТЕСТОВЫХ КЕЙСОВ (E8)
# ==========================================================
@router.post(
    "/check-in",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    payload: VisitEntryRequest,
    current_user=Depends(require_permission("visits.create")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /entry — регистрация входа клиента.
    """
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
    )
    return service._build_response(visit)


@router.post(
    "/check-out",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def check_out(
    payload: VisitExitRequest,
    current_user=Depends(require_permission("visits.update")),
    db: Session = Depends(get_db),
):
    """
    Алиас для /exit — регистрация выхода клиента.
    """
    service = VisitService(db)
    visit = service.exit(
        visit_id=str(payload.visit_id),
        exit_time=payload.exit_time,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(visit)


@router.post(
    "/{visit_id}/complete",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)'''

if old_exit in content:
    content = content.replace(old_exit, new_exit)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Алиасы /check-in и /check-out добавлены!")
else:
    print("ERROR: Не найдена точка вставки")
