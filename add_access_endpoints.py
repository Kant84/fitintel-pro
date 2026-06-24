# add_access_endpoints.py
with open('app/api/v1/access.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорты
old_imports = '''from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessGrantRequest,
    AccessGrantResponse,
    AccessExitRequest,
    AccessExitResponse,
)'''

new_imports = '''from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessGrantRequest,
    AccessGrantResponse,
    AccessExitRequest,
    AccessExitResponse,
    AccessOpenRequest,
    AccessOpenResponse,
    AccessManualOpenRequest,
    AccessManualOpenResponse,
    AccessStatusResponse,
    AccessBlockRequest,
    AccessBlockResponse,
    AccessLogResponse,
    AccessEmergencyUnlockResponse,
)'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    print("1. Импорты обновлены!")
else:
    print("ERROR 1: Не найдены импорты")

# Добавляем новые endpoint'ы в конец файла
new_endpoints = '''


# ==========================================================
# E9.1-3: ОТКРЫТИЕ ТУРНИКЕТА ПО КАРТЕ / QR
# ==========================================================

@router.post(
    "/open",
    response_model=AccessOpenResponse,
    status_code=status.HTTP_200_OK,
)
def open_access(
    payload: AccessOpenRequest,
    db: Session = Depends(get_db),
):
    """
    Открыть турникет по карте/QR (E9.1-E9.3).
    
    - Проверяет credential
    - Проверяет абонемент
    - Anti-passback
    - График доступа
    - Открывает устройство
    """
    service = AccessService(db)
    return service.open_access(
        credential=payload.credential,
        device_id=payload.device_id,
        zone=payload.zone,
    )


# ==========================================================
# E9.4-5: РУЧНОЕ ОТКРЫТИЕ (ADMIN)
# ==========================================================

@router.post(
    "/manual-open",
    response_model=AccessManualOpenResponse,
    status_code=status.HTTP_200_OK,
)
def manual_open(
    payload: AccessManualOpenRequest,
    current_user=Depends(require_permission("access.manual_open")),
    db: Session = Depends(get_db),
):
    """
    Ручное открытие турникета (E9.4-E9.5).
    
    - Требует право access.manual_open
    - Записывает причину в audit
    - Открывает без проверки абонемента
    """
    service = AccessService(db)
    return service.manual_open(
        device_id=payload.device_id,
        reason=payload.reason,
        opened_by_user_id=current_user.id,
    )


# ==========================================================
# E9.6: СТАТУС ТУРНИКЕТОВ
# ==========================================================

@router.get(
    "/status",
    response_model=AccessStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_access_status(
    current_user=Depends(require_permission("access.read")),
    db: Session = Depends(get_db),
):
    """
    Получить статус всех устройств доступа (E9.6).
    
    - Список турникетов с online/offline статусом
    - Требует право access.read
    """
    service = AccessService(db)
    return service.get_status()


# ==========================================================
# E9.7-8: БЛОКИРОВКА / РАЗБЛОКИРОВКА УСТРОЙСТВА
# ==========================================================

@router.post(
    "/{device_id}/block",
    response_model=AccessBlockResponse,
    status_code=status.HTTP_200_OK,
)
def block_device(
    device_id: str,
    payload: AccessBlockRequest,
    current_user=Depends(require_permission("access.manage")),
    db: Session = Depends(get_db),
):
    """
    Заблокировать устройство (E9.7).
    
    - Требует право access.manage
    - Устанавливает is_blocked = True
    """
    service = AccessService(db)
    return service.block_device(
        device_id=device_id,
        reason=payload.reason,
        blocked_by_user_id=current_user.id,
    )


@router.post(
    "/{device_id}/unblock",
    response_model=AccessBlockResponse,
    status_code=status.HTTP_200_OK,
)
def unblock_device(
    device_id: str,
    current_user=Depends(require_permission("access.manage")),
    db: Session = Depends(get_db),
):
    """
    Разблокировать устройство (E9.8).
    
    - Требует право access.manage
    - Устанавливает is_blocked = False
    """
    service = AccessService(db)
    return service.unblock_device(device_id=device_id)


# ==========================================================
# E9.9: ЛОГИ ДОСТУПА
# ==========================================================

@router.get(
    "/logs",
    response_model=AccessLogResponse,
    status_code=status.HTTP_200_OK,
)
def get_access_logs(
    date_from: str = None,
    date_to: str = None,
    device_id: str = None,
    current_user=Depends(require_permission("access.read")),
    db: Session = Depends(get_db),
):
    """
    Получить логи доступа (E9.9).
    
    - Фильтрация по дате и устройству
    - Требует право access.read
    """
    service = AccessService(db)
    return service.get_logs(
        date_from=date_from,
        date_to=date_to,
        device_id=device_id,
    )


# ==========================================================
# E9.13-14: ЭКСТРЕННОЕ ОТКРЫТИЕ
# ==========================================================

@router.post(
    "/emergency-unlock",
    response_model=AccessEmergencyUnlockResponse,
    status_code=status.HTTP_200_OK,
)
def emergency_unlock(
    current_user=Depends(require_permission("access.emergency")),
    db: Session = Depends(get_db),
):
    """
    Экстренное открытие всех турникетов (E9.13-E9.14).
    
    - Требует право access.emergency (SuperAdmin)
    - Открывает ВСЕ устройства
    - Записывает в audit
    """
    service = AccessService(db)
    return service.emergency_unlock(
        unlocked_by_user_id=current_user.id,
    )
'''

content = content + new_endpoints

with open('app/api/v1/access.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Новые endpoint'ы добавлены в access.py!")
