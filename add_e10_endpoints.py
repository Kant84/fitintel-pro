# add_e10_endpoints.py
with open('app/api/v1/credentials.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорты
old_imports = '''from app.schemas.credential import (
    CredentialResponse,
    CredentialListResponse,
    QRCreateRequest,
    QRResponse,
    RFIDCreateRequest,
    RFIDResponse,
    CredentialBlockRequest,
)'''

new_imports = '''from app.schemas.credential import (
    CredentialResponse,
    CredentialListResponse,
    QRCreateRequest,
    QRResponse,
    RFIDCreateRequest,
    RFIDResponse,
    CredentialBlockRequest,
    CardCreateRequest,
    BraceletCreateRequest,
    MobileKeyCreateRequest,
    CredentialReassignRequest,
    CredentialValidateResponse,
    CardReaderEmulateRequest,
    CardReaderEmulateResponse,
    MifareProgramRequest,
)'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    print("1. Импорты обновлены!")
else:
    print("ERROR 1: Не найдены импорты")

# Добавляем новые endpoint'ы в конец файла
new_endpoints = '''


# ==========================================================
# E10.1: СОЗДАНИЕ КАРТЫ (CARD)
# ==========================================================

@router.post(
    "/card",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    payload: CardCreateRequest,
    current_user=Depends(require_permission("credentials.create")),
    db: Session = Depends(get_db),
):
    """
    Создать карту доступа для клиента (E10.1).
    
    - Проверяет уникальность номера карты (E10.2)
    - Привязывает к клиенту
    """
    service = CredentialService(db)
    credential = service.create_card(
        client_id=str(payload.client_id),
        card_number=payload.card_number,
        valid_until=payload.valid_until,
        notes=payload.notes,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


# ==========================================================
# E10.3: СОЗДАНИЕ БРАСЛЕТА (BRACELET)
# ==========================================================

@router.post(
    "/bracelet",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bracelet(
    payload: BraceletCreateRequest,
    current_user=Depends(require_permission("credentials.create")),
    db: Session = Depends(get_db),
):
    """
    Создать браслет для клиента (E10.3).
    
    - Используется для KERONG шкафчиков
    - Проверяет уникальность RFID UID
    """
    service = CredentialService(db)
    credential = service.create_bracelet(
        client_id=str(payload.client_id),
        bracelet_id=payload.bracelet_id,
        rfid_manufacturer=payload.rfid_manufacturer,
        rfid_model=payload.rfid_model,
        valid_until=payload.valid_until,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


# ==========================================================
# E10.4: СОЗДАНИЕ МОБИЛЬНОГО КЛЮЧА (MOBILE_KEY)
# ==========================================================

@router.post(
    "/mobile-key",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mobile_key(
    payload: MobileKeyCreateRequest,
    current_user=Depends(require_permission("credentials.create")),
    db: Session = Depends(get_db),
):
    """
    Создать мобильный ключ для клиента (E10.4).
    
    - Привязывает мобильное устройство
    - Используется для Bluetooth/NFC доступа
    """
    service = CredentialService(db)
    credential = service.create_mobile_key(
        client_id=str(payload.client_id),
        device_id=payload.device_id,
        device_name=payload.device_name,
        valid_until=payload.valid_until,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


# ==========================================================
# E10.9: ПЕРЕПРИВЯЗКА КАРТЫ
# ==========================================================

@router.put(
    "/{credential_id}/reassign",
    response_model=CredentialResponse,
    status_code=status.HTTP_200_OK,
)
def reassign_credential(
    credential_id: UUID,
    payload: CredentialReassignRequest,
    current_user=Depends(require_permission("credentials.reassign")),
    db: Session = Depends(get_db),
):
    """
    Перепривязать credential к другому клиенту (E10.9).
    
    - Требует право credentials.reassign (SuperAdmin)
    - Сохраняет историю в audit
    """
    service = CredentialService(db)
    credential = service.reassign_credential(
        credential_id=str(credential_id),
        new_client_id=str(payload.new_client_id),
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


# ==========================================================
# E10.11-12: ВАЛИДАЦИЯ CREDENTIAL
# ==========================================================

@router.get(
    "/{credential_id}/validate",
    response_model=CredentialValidateResponse,
    status_code=status.HTTP_200_OK,
)
def validate_credential(
    credential_id: UUID,
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """
    Проверить валидность credential (E10.11-12).
    
    - Проверяет статус (ACTIVE/BLOCKED)
    - Проверяет срок действия
    - Проверяет активный абонемент
    """
    service = CredentialService(db)
    result = service.validate_credential(str(credential_id))
    return CredentialValidateResponse(**result)


# ==========================================================
# E10.13-14: ЭМУЛЯЦИЯ КАРД-РИДЕРА
# ==========================================================

@router.post(
    "/emulate",
    response_model=CardReaderEmulateResponse,
    status_code=status.HTTP_200_OK,
)
def emulate_card_reader(
    payload: CardReaderEmulateRequest,
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """
    Эмулировать кард-ридер (E10.13-14).
    
    - Парсит сырые данные с кард-ридера
    - Поддерживает Wiegand-26, Wiegand-34, Magstripe
    - Ищет credential в БД
    """
    service = CredentialService(db)
    result = service.emulate_card_reader(
        card_data=payload.card_data,
        format=payload.format or "auto",
    )
    return CardReaderEmulateResponse(**result)


# ==========================================================
# E10.15: ПРОГРАММИРОВАНИЕ MIFARE
# ==========================================================

@router.post(
    "/{credential_id}/program",
    status_code=status.HTTP_200_OK,
)
def program_mifare(
    credential_id: UUID,
    payload: MifareProgramRequest,
    current_user=Depends(require_permission("credentials.manage")),
    db: Session = Depends(get_db),
):
    """
    Программировать MIFARE карту (E10.15).
    
    - Записывает данные в сектор
    - Использует Key A для аутентификации
    - Сохраняет данные в credential.config
    """
    service = CredentialService(db)
    result = service.program_mifare(
        credential_id=str(credential_id),
        sector=payload.sector,
        key_a=payload.key_a,
        data=payload.data,
        actor_user_id=str(current_user.id),
    )
    return result
'''

content = content + new_endpoints

with open('app/api/v1/credentials.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("E10 endpoint'ы добавлены!")
