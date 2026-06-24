# app/api/v1/credentials.py

from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.credential import (
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
)
from app.services.credential_service import CredentialService
from app.services.qr_service import QRService


router = APIRouter(prefix="/credentials", tags=["Credentials"])


# ==========================================================
# QR-КОДЫ
# ==========================================================

@router.post(
    "/qr",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_qr(
    payload: QRCreateRequest,
    current_user=Depends(require_permission("credentials.create")),
    db: Session = Depends(get_db),
):
    """
    Создать QR-код для клиента.
    
    - Генерирует уникальный QR-код
    - Привязывает к клиенту
    - Возвращает QR-код для отображения
    """
    service = CredentialService(db)
    credential = service.create_qr(
        client_id=str(payload.client_id),
        valid_until=payload.valid_until,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


@router.get(
    "/qr/client/{client_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def get_client_qr(
    client_id: UUID,
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """
    Получить QR-код клиента с изображением.
    
    - Возвращает QR-код в формате base64
    - Для отображения в личном кабинете
    """
    service = QRService(db)
    qr_data = service.get_client_qr(str(client_id))
    
    if not qr_data:
        return {"has_qr": False}
    
    return {"has_qr": True, **qr_data}


@router.post(
    "/qr/client/{client_id}/regenerate",
    response_model=CredentialResponse,
    status_code=status.HTTP_200_OK,
)
def regenerate_qr(
    client_id: UUID,
    current_user=Depends(require_permission("credentials.update")),
    db: Session = Depends(get_db),
):
    """
    Перевыпустить QR-код для клиента.
    
    - Блокирует старый QR-код
    - Создаёт новый
    - Используется при утере или подозрении на компрометацию
    """
    service = CredentialService(db)
    credential = service.regenerate_qr(
        client_id=str(client_id),
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


# ==========================================================
# RFID-МЕТКИ
# ==========================================================

@router.post(
    "/rfid",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rfid(
    payload: RFIDCreateRequest,
    current_user=Depends(require_permission("credentials.create")),
    db: Session = Depends(get_db),
):
    """
    Привязать RFID-метку к клиенту.
    
    - Используется для браслетов KERONG
    - Проверяет уникальность UID
    """
    service = CredentialService(db)
    credential = service.create_rfid(
        client_id=str(payload.client_id),
        credential_value=payload.credential_value,
        rfid_manufacturer=payload.rfid_manufacturer,
        rfid_model=payload.rfid_model,
        valid_until=payload.valid_until,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


@router.get(
    "/rfid/client/{client_id}",
    response_model=CredentialListResponse,
    status_code=status.HTTP_200_OK,
)
def get_client_rfid(
    client_id: UUID,
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """Получить все RFID-метки клиента"""
    service = CredentialService(db)
    credentials = service.get_client_rfid(str(client_id))
    
    return CredentialListResponse(
        items=[service._build_response(c) for c in credentials],
        count=len(credentials),
    )


# ==========================================================
# УПРАВЛЕНИЕ УЧЁТНЫМИ ДАННЫМИ
# ==========================================================

@router.get(
    "/client/{client_id}",
    response_model=CredentialListResponse,
    status_code=status.HTTP_200_OK,
)
def get_client_credentials(
    client_id: UUID,
    credential_type: str | None = Query(default=None, description="QR, RFID"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """Получить все учётные данные клиента"""
    service = CredentialService(db)
    return service.get_client_credentials(
        client_id=str(client_id),
        credential_type=credential_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{credential_id}",
    response_model=CredentialResponse,
    status_code=status.HTTP_200_OK,
)
def get_credential(
    credential_id: UUID,
    current_user=Depends(require_permission("credentials.read")),
    db: Session = Depends(get_db),
):
    """Получить учётные данные по ID"""
    service = CredentialService(db)
    credential = service.get_credential(str(credential_id))
    return service._build_response(credential)


@router.post(
    "/{credential_id}/block",
    response_model=CredentialResponse,
    status_code=status.HTTP_200_OK,
)
def block_credential(
    credential_id: UUID,
    payload: CredentialBlockRequest,
    current_user=Depends(require_permission("credentials.update")),
    db: Session = Depends(get_db),
):
    """Заблокировать учётные данные"""
    service = CredentialService(db)
    credential = service.block_credential(
        credential_id=str(credential_id),
        reason=payload.reason,
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


@router.post(
    "/{credential_id}/unblock",
    response_model=CredentialResponse,
    status_code=status.HTTP_200_OK,
)
def unblock_credential(
    credential_id: UUID,
    current_user=Depends(require_permission("credentials.update")),
    db: Session = Depends(get_db),
):
    """Разблокировать учётные данные"""
    service = CredentialService(db)
    credential = service.unblock_credential(
        credential_id=str(credential_id),
        actor_user_id=str(current_user.id),
    )
    return service._build_response(credential)


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_credential(
    credential_id: UUID,
    current_user=Depends(require_permission("credentials.delete")),
    db: Session = Depends(get_db),
):
    """Удалить учётные данные"""
    service = CredentialService(db)
    service.delete_credential(
        credential_id=str(credential_id),
        actor_user_id=str(current_user.id),
    )
    return None



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
