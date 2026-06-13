# app/services/credential_service.py

from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.credential import Credential
from app.models.client import Client
from app.repositories.credential_repository import CredentialRepository
from app.services.audit_service import AuditService
from app.services.qr_service import QRService
from app.schemas.credential import (
    CredentialResponse,
    CredentialListResponse,
    QRCreateRequest,
    QRResponse,
    RFIDCreateRequest,
    RFIDResponse,
    CredentialBlockRequest,
)
from app.schemas.enums import CredentialType, CredentialStatus


class CredentialService:
    """
    Сервис для управления учётными данными (QR-коды, RFID-метки).
    
    Включает:
    - Создание и управление QR-кодами
    - Привязку RFID-меток
    - Блокировку/разблокировку учётных данных
    - Проверку прав доступа
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CredentialRepository(db)
        self.qr_service = QRService(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_client(self, client_id: str) -> Client:
        """Получить клиента или выбросить 404"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден"
            )
        return client
    
    def _build_response(self, credential: Credential) -> dict:
        """Построить словарь ответа"""
        return {
            "id": credential.id,
            "client_id": credential.client_id,
            "credential_type": credential.credential_type,
            "credential_value": credential.credential_value,
            "status": credential.status,
            "valid_from": credential.valid_from,
            "valid_until": credential.valid_until,
            "qr_version": credential.qr_version,
            "qr_format": credential.qr_format,
            "rfid_manufacturer": credential.rfid_manufacturer,
            "rfid_model": credential.rfid_model,
            "issued_by_user_id": credential.issued_by_user_id,
            "issued_at": credential.issued_at,
            "notes": credential.notes,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
        }
    
    # ==========================================================
    # QR-КОДЫ
    # ==========================================================
    
    def create_qr(
        self,
        client_id: str,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """
        Создать QR-код для клиента.
        
        Args:
            client_id: ID клиента
            valid_until: Дата окончания действия
            actor_user_id: ID пользователя, выполняющего действие
        
        Returns:
            Созданные учётные данные
        """
        # Проверяем клиента
        client = self._get_client(client_id)
        
        # Проверяем, есть ли уже активный QR-код
        existing = self.repository.get_by_client_and_type(client_id, "QR")
        if existing and existing.status == "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="У клиента уже есть активный QR-код. Сначала заблокируйте его."
            )
        
        # Создаём QR-код
        credential = self.qr_service.create_qr_credential(
            client_id=client_id,
            valid_until=valid_until,
            issued_by_user_id=actor_user_id,
        )
        
        # Логируем
        self.audit.log(
            action="credential.qr.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"QR code created for client {client.first_name} {client.last_name}",
        )
        
        return credential
    
    def get_client_qr(self, client_id: str) -> dict | None:
        """Получить QR-код клиента с изображением"""
        return self.qr_service.get_client_qr(client_id)
    
    def regenerate_qr(self, client_id: str, actor_user_id: str | None = None) -> Credential:
        """Перевыпустить QR-код"""
        client = self._get_client(client_id)
        
        new_qr = self.qr_service.regenerate_qr(client_id, actor_user_id)
        
        self.audit.log(
            action="credential.qr.regenerated",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=new_qr.id,
            message=f"QR code regenerated for client {client.first_name} {client.last_name}",
        )
        
        return new_qr
    
    # ==========================================================
    # RFID-МЕТКИ
    # ==========================================================
    
    def create_rfid(
        self,
        client_id: str,
        credential_value: str,
        rfid_manufacturer: str | None = None,
        rfid_model: str | None = None,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """
        Привязать RFID-метку к клиенту.
        
        Args:
            client_id: ID клиента
            credential_value: UID RFID-метки
            rfid_manufacturer: Производитель (например, KERONG)
            rfid_model: Модель метки
            valid_until: Дата окончания действия
            actor_user_id: ID пользователя, выполняющего действие
        
        Returns:
            Созданные учётные данные
        """
        # Проверяем клиента
        client = self._get_client(client_id)
        
        # Проверяем, не используется ли уже эта метка
        if self.repository.exists_by_value(credential_value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="RFID-метка уже привязана к другому клиенту"
            )
        
        # Если не указана дата окончания — 1 год
        if valid_until is None:
            valid_until = date.today() + timedelta(days=365)
        
        # Создаём учётные данные
        credential = Credential(
            client_id=client_id,
            credential_type="RFID",
            credential_value=credential_value,
            status="ACTIVE",
            valid_from=date.today(),
            valid_until=valid_until,
            rfid_manufacturer=rfid_manufacturer,
            rfid_model=rfid_model,
            issued_by_user_id=actor_user_id,
            issued_at=datetime.now(),
        )
        
        created = self.repository.add(credential)
        
        self.audit.log(
            action="credential.rfid.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=created.id,
            message=f"RFID tag {credential_value} assigned to client {client.first_name} {client.last_name}",
        )
        
        return created
    
    def get_client_rfid(self, client_id: str) -> List[Credential]:
        """Получить все RFID-метки клиента"""
        return self.repository.list_by_client(
            client_id=client_id,
            credential_type="RFID",
            status="ACTIVE",
        )
    
    # ==========================================================
    # УПРАВЛЕНИЕ УЧЁТНЫМИ ДАННЫМИ
    # ==========================================================
    
    def get_credential(self, credential_id: str) -> Credential:
        """Получить учётные данные по ID"""
        credential = self.repository.get_by_id(credential_id)
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Учётные данные не найдены"
            )
        return credential
    
    def get_client_credentials(
        self,
        client_id: str,
        credential_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CredentialListResponse:
        """Получить все учётные данные клиента"""
        client = self._get_client(client_id)
        
        credentials = self.repository.list_by_client(
            client_id=client_id,
            credential_type=credential_type,
            limit=limit,
            offset=offset,
        )
        
        return CredentialListResponse(
            items=[self._build_response(c) for c in credentials],
            count=len(credentials),
        )
    
    def block_credential(
        self,
        credential_id: str,
        reason: str,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Заблокировать учётные данные"""
        credential = self.get_credential(credential_id)
        
        if credential.status == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Учётные данные уже заблокированы"
            )
        
        blocked = self.repository.block(credential_id, reason)
        
        self.audit.log(
            action="credential.blocked",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential_id,
            message=f"Credential {credential.credential_type} blocked. Reason: {reason}",
        )
        
        return blocked
    
    def unblock_credential(
        self,
        credential_id: str,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Разблокировать учётные данные"""
        credential = self.get_credential(credential_id)
        
        if credential.status != "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Учётные данные не заблокированы"
            )
        
        unblocked = self.repository.unblock(credential_id)
        
        self.audit.log(
            action="credential.unblocked",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential_id,
            message=f"Credential {credential.credential_type} unblocked",
        )
        
        return unblocked
    
    def delete_credential(
        self,
        credential_id: str,
        actor_user_id: str | None = None,
    ) -> None:
        """Удалить учётные данные"""
        credential = self.get_credential(credential_id)
        
        self.repository.delete(credential)
        
        self.audit.log(
            action="credential.deleted",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential_id,
            message=f"Credential {credential.credential_type} deleted",
        )
    
    # ==========================================================
    # ПРОВЕРКА ДОСТУПА
    # ==========================================================
    
    def check_credential(self, credential_value: str) -> Tuple[bool, str | None, str | None]:
        """
        Проверить валидность учётных данных.
        
        Returns:
            (is_valid, client_id, reason)
        """
        # Сначала проверяем как QR-код
        is_valid, client_id, reason = self.qr_service.validate_qr(credential_value)
        
        if is_valid:
            return True, client_id, None
        
        # Если не QR, ищем как RFID
        credential = self.repository.get_by_value(credential_value)
        
        if not credential:
            return False, None, "Учётные данные не найдены"
        
        if credential.credential_type != "RFID":
            return False, None, "Неверный тип учётных данных"
        
        if credential.status != "ACTIVE":
            return False, None, f"Учётные данные {credential.status}"
        
        # Проверяем срок действия
        today = date.today()
        if credential.valid_from > today:
            return False, None, "Учётные данные ещё не активны"
        
        if credential.valid_until and credential.valid_until < today:
            return False, None, "Учётные данные просрочены"
        
        return True, credential.client_id, None
    
    # ==========================================================
    # ФОНОВЫЕ ЗАДАЧИ
    # ==========================================================
    
    def expire_old_credentials(self) -> int:
        """Пометить просроченные учётные данные как EXPIRED"""
        return self.repository.expire_old_credentials()