# app/services/credential_service.py

from datetime import datetime, date, timedelta, timezone
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
    
    # ==========================================================
    # E10.1: СОЗДАНИЕ КАРТЫ (CARD)
    # ==========================================================
    
    def create_card(
        self,
        client_id: str,
        card_number: str,
        valid_until: date | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать карту доступа для клиента (E10.1)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность номера карты (E10.2)
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "CARD",
            Credential.credential_value == card_number,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Карта с таким номером уже существует",
            )
        
        # Создаём карту
        credential = Credential(
            client_id=client.id,
            credential_type="CARD",
            credential_value=card_number,
            status="ACTIVE",
            valid_until=valid_until,
            notes=notes,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.card.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Card created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "card_number": card_number,
                "valid_until": str(valid_until) if valid_until else None,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.3: СОЗДАНИЕ БРАСЛЕТА (BRACELET)
    # ==========================================================
    
    def create_bracelet(
        self,
        client_id: str,
        bracelet_id: str,
        rfid_manufacturer: str | None = None,
        rfid_model: str | None = None,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать браслет для клиента (E10.3)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "BRACELET",
            Credential.credential_value == bracelet_id,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Браслет с таким ID уже существует",
            )
        
        credential = Credential(
            client_id=client.id,
            credential_type="BRACELET",
            credential_value=bracelet_id,
            status="ACTIVE",
            rfid_manufacturer=rfid_manufacturer,
            rfid_model=rfid_model,
            valid_until=valid_until,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.bracelet.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Bracelet created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "bracelet_id": bracelet_id,
                "rfid_manufacturer": rfid_manufacturer,
                "rfid_model": rfid_model,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.4: СОЗДАНИЕ МОБИЛЬНОГО КЛЮЧА (MOBILE_KEY)
    # ==========================================================
    
    def create_mobile_key(
        self,
        client_id: str,
        device_id: str,
        device_name: str | None = None,
        valid_until: date | None = None,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Создать мобильный ключ для клиента (E10.4)"""
        client = self._get_client(client_id)
        
        # Проверяем уникальность device_id
        existing = self.db.query(Credential).filter(
            Credential.credential_type == "MOBILE_KEY",
            Credential.credential_value == device_id,
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Мобильный ключ для этого устройства уже существует",
            )
        
        credential = Credential(
            client_id=client.id,
            credential_type="MOBILE_KEY",
            credential_value=device_id,
            status="ACTIVE",
            rfid_model=device_name,
            valid_until=valid_until,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.mobile_key.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Mobile key created for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "device_id": device_id,
                "device_name": device_name,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.9: ПЕРЕПРИВЯЗКА КАРТЫ
    # ==========================================================
    
    def reassign_credential(
        self,
        credential_id: str,
        new_client_id: str,
        actor_user_id: str | None = None,
    ) -> Credential:
        """Перепривязать credential к другому клиенту (E10.9)"""
        credential = self.get_credential(credential_id)
        old_client_id = credential.client_id
        
        # Проверяем нового клиента
        new_client = self._get_client(new_client_id)
        
        # Сохраняем старые данные для audit
        old_data = {
            "client_id": str(credential.client_id),
            "credential_type": credential.credential_type,
            "credential_value": credential.credential_value,
        }
        
        # Перепривязываем
        credential.client_id = new_client.id
        self.db.commit()
        self.db.refresh(credential)
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.reassigned",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"Credential reassigned from client {old_client_id} to {new_client.first_name} {new_client.last_name}",
            before_data=old_data,
            after_data={
                "new_client_id": str(new_client.id),
                "credential_type": credential.credential_type,
            },
        )
        
        return credential
    
    # ==========================================================
    # E10.11-12: ВАЛИДАЦИЯ CREDENTIAL
    # ==========================================================
    
    def validate_credential(
        self,
        credential_id: str,
    ) -> dict:
        """Проверить валидность credential (E10.11-12)"""
        credential = self.db.query(Credential).filter(
            Credential.id == credential_id,
        ).first()
        
        if not credential:
            return {
                "valid": False,
                "reason": "Credential не найден",
            }
        
        # Проверяем статус
        if credential.status != "ACTIVE":
            return {
                "valid": False,
                "credential_id": credential.id,
                "credential_type": credential.credential_type,
                "client_id": credential.client_id,
                "reason": "blocked" if credential.status == "BLOCKED" else f"status={credential.status}",
            }
        
        # Проверяем срок действия
        if credential.valid_until and credential.valid_until < date.today():
            return {
                "valid": False,
                "credential_id": credential.id,
                "credential_type": credential.credential_type,
                "client_id": credential.client_id,
                "reason": "expired",
            }
        
        # Проверяем абонемент
        from app.models.subscription import Subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.client_id == credential.client_id,
            Subscription.is_active == True,
            Subscription.end_date >= date.today(),
        ).first()
        
        client = self._get_client(str(credential.client_id))
        
        return {
            "valid": True,
            "credential_id": credential.id,
            "credential_type": credential.credential_type,
            "client_id": credential.client_id,
            "client_name": f"{client.first_name} {client.last_name}",
            "subscription_active": subscription is not None,
            "subscription_end_date": subscription.end_date if subscription else None,
        }
    
    # ==========================================================
    # E10.13-14: ЭМУЛЯЦИЯ КАРД-РИДЕРА
    # ==========================================================
    
    def emulate_card_reader(
        self,
        card_data: str,
        format: str = "auto",
    ) -> dict:
        """Эмулировать кард-ридер (E10.13-14)"""
        card_number = None
        
        # Парсим данные в зависимости от формата
        if format == "auto":
            # Пробуем разные форматы
            # Wiegand 26: 3 байта (24 бита) + 2 parity
            if len(card_data) == 8 and all(c in "0123456789ABCDEF" for c in card_data.upper()):
                card_number = card_data.upper()
            # Wiegand 34: 4 байта (32 бита) + 2 parity
            elif len(card_data) == 10 and all(c in "0123456789ABCDEF" for c in card_data.upper()):
                card_number = card_data.upper()
            # Magstripe: ;1234567890=1234?
            elif card_data.startswith(";") and "=" in card_data:
                parts = card_data.strip(";?").split("=")
                if parts:
                    card_number = parts[0]
            # Просто номер
            elif card_data.isdigit():
                card_number = card_data
            else:
                return {
                    "success": False,
                    "reason": "Неподдерживаемый формат карты",
                }
        elif format == "wiegand26":
            if len(card_data) == 8:
                card_number = card_data.upper()
            else:
                return {"success": False, "reason": "Неверная длина Wiegand-26"}
        elif format == "wiegand34":
            if len(card_data) == 10:
                card_number = card_data.upper()
            else:
                return {"success": False, "reason": "Неверная длина Wiegand-34"}
        elif format == "magstripe":
            if card_data.startswith(";") and "=" in card_data:
                parts = card_data.strip(";?").split("=")
                card_number = parts[0] if parts else None
            else:
                return {"success": False, "reason": "Неверный формат магнитной полосы"}
        else:
            return {"success": False, "reason": f"Неизвестный формат: {format}"}
        
        if not card_number:
            return {"success": False, "reason": "Не удалось извлечь номер карты"}
        
        # Ищем credential
        credential = self.db.query(Credential).filter(
            Credential.credential_value == card_number,
            Credential.status == "ACTIVE",
        ).first()
        
        if credential:
            client = self._get_client(str(credential.client_id))
            return {
                "success": True,
                "card_number": card_number,
                "credential_id": credential.id,
                "client_id": credential.client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "credential_type": credential.credential_type,
            }
        else:
            return {
                "success": True,
                "card_number": card_number,
                "reason": "Карта не найдена в системе",
            }
    
    # ==========================================================
    # E10.15: ПРОГРАММИРОВАНИЕ MIFARE
    # ==========================================================
    
    def program_mifare(
        self,
        credential_id: str,
        sector: int,
        key_a: str,
        data: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        """Программировать MIFARE карту (E10.15)"""
        credential = self.get_credential(credential_id)
        
        # Проверяем, что это карта или браслет
        if credential.credential_type not in ["CARD", "BRACELET", "RFID"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Только карты и браслеты поддерживают MIFARE программирование",
            )
        
        # Проверяем формат ключа (12 hex символов)
        if len(key_a) != 12 or not all(c in "0123456789ABCDEFabcdef" for c in key_a):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ключ A должен быть 12 hex символов",
            )
        
        # Проверяем данные (32 hex символа = 16 байт)
        if data and (len(data) != 32 or not all(c in "0123456789ABCDEFabcdef" for c in data)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные должны быть 32 hex символа (16 байт)",
            )
        
        # Здесь должна быть реальная запись на карту через кард-ридер
        # Сейчас — заглушка (симуляция)
        programmed_data = {
            "sector": sector,
            "key_a": key_a.upper(),
            "data": (data or "0" * 32).upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Сохраняем в credential.config
        if not credential.config:
            credential.config = {}
        if isinstance(credential.config, dict):
            credential.config["mifare"] = programmed_data
        self.db.commit()
        
        # Audit
        from app.services.audit_service import AuditService
        audit = AuditService(self.db)
        audit.log(
            action="credentials.mifare.programmed",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="credential",
            entity_id=credential.id,
            message=f"MIFARE sector {sector} programmed",
            after_data=programmed_data,
        )
        
        return {
            "success": True,
            "credential_id": credential.id,
            "sector": sector,
            "key_a": key_a.upper(),
            "data": (data or "0" * 32).upper(),
            "message": "Карта запрограммирована (симуляция)",
        }
    
    # ==========================================================
    # E10.2: ПРОВЕРКА ДУБЛИКАТА
    # ==========================================================
    
    def check_duplicate(
        self,
        credential_type: str,
        credential_value: str,
    ) -> bool:
        """Проверить, существует ли credential с таким значением (E10.2)"""
        existing = self.db.query(Credential).filter(
            Credential.credential_type == credential_type,
            Credential.credential_value == credential_value,
        ).first()
        return existing is not None
    
    def expire_old_credentials(self) -> int:
        """Пометить просроченные учётные данные как EXPIRED"""
        return self.repository.expire_old_credentials()