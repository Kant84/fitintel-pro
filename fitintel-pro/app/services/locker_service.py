# app/services/locker_service.py

from datetime import datetime, date
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.locker import Locker
from app.models.locker_session import LockerSession
from app.models.locker_privilege import LockerPrivilege
from app.models.credential import Credential
from app.models.client import Client
from app.repositories.locker_repository import LockerRepository
from app.repositories.locker_session_repository import LockerSessionRepository
from app.repositories.locker_privilege_repository import LockerPrivilegeRepository
from app.repositories.credential_repository import CredentialRepository
from app.services.audit_service import AuditService
from app.schemas.enums import LockType, LockerStatus, LockerSessionStatus, LockerPrivilegeType


class LockerService:
    """
    Сервис для управления шкафчиками и замками.
    
    Поддерживает два типа замков:
    - OFFLINE (KERONG офлайн): закрывается любым браслетом,
      инфотерминал только подсказывает номер шкафа
    - ONLINE (KERONG онлайн): закрывается только при наличии привилегии,
      блокирует выход клиента
    
    Также поддерживает привилегии для VIP и арендных шкафов.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.locker_repo = LockerRepository(db)
        self.session_repo = LockerSessionRepository(db)
        self.privilege_repo = LockerPrivilegeRepository(db)
        self.credential_repo = CredentialRepository(db)
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
    
    def _get_credential(self, credential_value: str) -> Tuple[Credential, Client]:
        """
        Получить учётные данные и клиента по значению.
        
        Returns:
            (credential, client)
        """
        credential = self.credential_repo.get_by_value(credential_value)
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Учётные данные не найдены"
            )
        
        client = self._get_client(credential.client_id)
        return credential, client
    
    def _send_lock_command(self, device_id: str, command: str) -> bool:
        """
        Отправить команду на замок KERONG.
        
        Args:
            device_id: ID устройства замка
            command: CLOSE, OPEN
        
        Returns:
            True если команда отправлена успешно
        """
        # TODO: Реальная интеграция с KERONG
        # Пока эмуляция
        print(f"[KERONG] Device {device_id}: {command} command sent")
        return True
    
    def _has_privilege(self, client_id: str, locker_type: str) -> bool:
        """Проверить, есть ли у клиента привилегия на тип шкафчика"""
        return self.privilege_repo.has_privilege(client_id, locker_type)
    
    # ==========================================================
    # ИНФОТЕРМИНАЛ: ПОДСКАЗКА НОМЕРА ШКАФА (OFFLINE)
    # ==========================================================
    
    def get_locker_info(
        self,
        credential_value: str,
        terminal_id: str,
    ) -> dict:
        """
        Инфотерминал: показать номер шкафчика по браслету.
        
        Для OFFLINE замков — только подсказка, без изменения статуса.
        Для ONLINE замков — также показывает активную сессию.
        
        Args:
            credential_value: UID браслета или QR-код
            terminal_id: ID инфотерминала
        
        Returns:
            Информация о шкафчике
        """
        credential, client = self._get_credential(credential_value)
        
        # Ищем активную сессию
        active_session = self.session_repo.get_active_by_client(client.id)
        
        if not active_session:
            return {
                "has_locker": False,
                "locker_number": None,
                "lock_type": None,
                "message": "У вас нет активного шкафчика",
            }
        
        locker = self.locker_repo.get_by_id(active_session.locker_id)
        
        # Обновляем info_terminal_id (для OFFLINE замков)
        if locker.lock_type == LockType.OFFLINE.value:
            active_session.info_terminal_id = terminal_id
            self.db.commit()
        
        return {
            "has_locker": True,
            "locker_number": locker.number,
            "lock_type": locker.lock_type,
            "message": f"Ваш шкафчик №{locker.number}",
        }
    
    # ==========================================================
    # ONLINE ЗАМКИ: ВЫБОР И ЗАКРЫТИЕ ШКАФЧИКА
    # ==========================================================
    
    def select_locker(
        self,
        locker_number: str,
        credential_value: str,
        terminal_id: str,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Выбрать и закрыть онлайн шкафчик (только для ONLINE замков).
        
        Процесс:
        1. Клиент выбирает свободный шкафчик на терминале
        2. Прикладывает браслет к считывателю
        3. Система проверяет права
        4. Отправляет команду на закрытие замка
        5. Создаётся сессия
        
        Args:
            locker_number: Номер выбранного шкафчика
            credential_value: UID браслета
            terminal_id: ID инфотерминала
            actor_user_id: ID менеджера (если принудительно)
        
        Returns:
            Результат операции
        """
        credential, client = self._get_credential(credential_value)
        
        # Находим шкафчик
        locker = self.locker_repo.get_by_number(locker_number)
        if not locker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шкафчик не найден"
            )
        
        # Проверяем, что это ONLINE замок
        if locker.lock_type != LockType.ONLINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Шкафчик №{locker_number} не является онлайн замком"
            )
        
        # Проверяем, свободен ли шкафчик
        if locker.status != LockerStatus.FREE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Шкафчик №{locker_number} уже занят"
            )
        
        # Проверяем, нет ли у клиента активной сессии
        active_session = self.session_repo.get_active_by_client(client.id)
        if active_session:
            existing_locker = self.locker_repo.get_by_id(active_session.locker_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"У вас уже есть активный шкафчик №{existing_locker.number}"
            )
        
        # Проверяем привилегии (если требуется)
        if locker.requires_privilege:
            if not self._has_privilege(client.id, LockerPrivilegeType.VIP.value):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У вас нет прав на использование этого шкафчика"
                )
        
        # Отправляем команду на закрытие замка
        if locker.device_id:
            self._send_lock_command(locker.device_id, "CLOSE")
        
        # Создаём сессию
        session = LockerSession(
            locker_id=locker.id,
            client_id=client.id,
            credential_id=credential.id,
            lock_type=LockType.ONLINE.value,
            started_at=datetime.now(),
            status=LockerSessionStatus.ACTIVE.value,
            register_terminal_id=terminal_id,
        )
        self.db.add(session)
        
        # Обновляем статус шкафчика
        locker.status = LockerStatus.OCCUPIED.value
        
        self.db.commit()
        
        # Логируем
        self.audit.log(
            action="locker.selected",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker_number} selected by client {client.first_name} {client.last_name}",
        )
        
        return {
            "success": True,
            "locker_number": locker.number,
            "message": f"Шкафчик №{locker.number} закрыт",
        }
    
    # ==========================================================
    # ONLINE ЗАМКИ: ОТКРЫТИЕ ШКАФЧИКА (ВЫХОД)
    # ==========================================================
    
    def release_locker(
        self,
        credential_value: str,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Открыть онлайн шкафчик (при выходе).
        
        Args:
            credential_value: UID браслета
            actor_user_id: ID менеджера (если принудительно)
        
        Returns:
            Результат операции
        """
        credential, client = self._get_credential(credential_value)
        
        # Находим активную сессию
        active_session = self.session_repo.get_active_by_client(client.id)
        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="У вас нет активного шкафчика"
            )
        
        # Проверяем тип замка
        if active_session.lock_type != LockType.ONLINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот шкафчик не является онлайн замком"
            )
        
        locker = self.locker_repo.get_by_id(active_session.locker_id)
        
        # Отправляем команду на открытие замка
        if locker.device_id:
            self._send_lock_command(locker.device_id, "OPEN")
        
        # Закрываем сессию
        active_session.status = LockerSessionStatus.CLOSED.value
        active_session.ended_at = datetime.now()
        
        # Обновляем статус шкафчика
        locker.status = LockerStatus.FREE.value
        
        self.db.commit()
        
        # Логируем
        self.audit.log(
            action="locker.released",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker.number} released by client {client.first_name} {client.last_name}",
        )
        
        return {
            "success": True,
            "locker_number": locker.number,
            "message": f"Шкафчик №{locker.number} открыт",
        }
    
    # ==========================================================
    # OFFLINE ЗАМКИ: РЕГИСТРАЦИЯ БРАСЛЕТА (ВЫДАЧА ПРИВИЛЕГИЙ)
    # ==========================================================
    
    def register_offline_bracelet(
        self,
        client_id: str,
        credential_value: str,
        locker_number: str,
        actor_user_id: str | None = None,
    ) -> dict:
        """
        Зарегистрировать браслет для офлайн замка.
        
        На ресепшене программируют браслет и привязывают к шкафчику.
        
        Args:
            client_id: ID клиента
            credential_value: UID браслета
            locker_number: Номер шкафчика
            actor_user_id: ID менеджера
        
        Returns:
            Результат регистрации
        """
        client = self._get_client(client_id)
        
        # Находим шкафчик
        locker = self.locker_repo.get_by_number(locker_number)
        if not locker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шкафчик не найден"
            )
        
        # Проверяем, что это OFFLINE замок
        if locker.lock_type != LockType.OFFLINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Шкафчик №{locker_number} не является офлайн замком"
            )
        
        # Проверяем, не используется ли уже браслет
        if self.credential_repo.exists_by_value(credential_value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Браслет уже зарегистрирован"
            )
        
        # Создаём учётные данные
        credential = Credential(
            client_id=client.id,
            credential_type="RFID",
            credential_value=credential_value,
            status="ACTIVE",
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=365),
            rfid_manufacturer="KERONG",
            issued_by_user_id=actor_user_id,
            issued_at=datetime.now(),
            notes=f"Офлайн замок, шкафчик №{locker_number}",
        )
        self.db.add(credential)
        
        # Создаём сессию (для подсказки на инфотерминале)
        session = LockerSession(
            locker_id=locker.id,
            client_id=client.id,
            credential_id=credential.id,
            lock_type=LockType.OFFLINE.value,
            started_at=datetime.now(),
            status=LockerSessionStatus.ACTIVE.value,
            notes=f"Зарегистрирован менеджером",
        )
        self.db.add(session)
        
        # Обновляем статус шкафчика
        locker.status = LockerStatus.OCCUPIED.value
        
        self.db.commit()
        
        self.audit.log(
            action="locker.offline.register",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Offline bracelet {credential_value} registered for locker {locker_number}",
        )
        
        return {
            "success": True,
            "locker_number": locker.number,
            "message": f"Браслет зарегистрирован для шкафчика №{locker_number}",
        }
    
    # ==========================================================
    # УПРАВЛЕНИЕ ШКАФЧИКАМИ (АДМИНИСТРИРОВАНИЕ)
    # ==========================================================
    
    def create_locker(
        self,
        number: str,
        lock_type: str,
        zone: str | None = None,
        requires_privilege: bool = False,
        device_id: str | None = None,
        notes: str | None = None,
    ) -> Locker:
        """Создать новый шкафчик"""
        # Проверяем уникальность номера
        existing = self.locker_repo.get_by_number(number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Шкафчик с номером {number} уже существует"
            )
        
        locker = Locker(
            number=number,
            zone=zone,
            lock_type=lock_type,
            status=LockerStatus.FREE.value,
            device_id=device_id,
            requires_privilege=requires_privilege,
            notes=notes,
        )
        
        return self.locker_repo.add(locker)
    
    def get_free_lockers(
        self,
        lock_type: str | None = None,
        zone: str | None = None,
    ) -> List[Locker]:
        """Получить список свободных шкафчиков"""
        return self.locker_repo.get_free_lockers(lock_type=lock_type, zone=zone)
    
    def get_locker_status(self, locker_number: str) -> dict:
        """Получить статус шкафчика"""
        locker = self.locker_repo.get_by_number(locker_number)
        if not locker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шкафчик не найден"
            )
        
        active_session = self.session_repo.get_active_by_locker(locker.id)
        
        return {
            "locker": {
                "id": locker.id,
                "number": locker.number,
                "zone": locker.zone,
                "lock_type": locker.lock_type,
                "status": locker.status,
                "requires_privilege": locker.requires_privilege,
            },
            "is_occupied": active_session is not None,
            "client": {
                "id": active_session.client_id,
                "name": active_session.client.first_name + " " + active_session.client.last_name if active_session else None,
            } if active_session else None,
        }
    
    def get_client_active_locker(self, client_id: str) -> dict | None:
        """Получить активный шкафчик клиента"""
        active_session = self.session_repo.get_active_by_client(client_id)
        if not active_session:
            return None
        
        locker = self.locker_repo.get_by_id(active_session.locker_id)
        
        return {
            "locker_number": locker.number,
            "lock_type": locker.lock_type,
            "started_at": active_session.started_at,
            "status": active_session.status,
        }
    
    def admin_force_release(
        self,
        locker_number: str,
        actor_user_id: str,
        reason: str | None = None,
    ) -> dict:
        """
        Принудительное освобождение шкафчика (администратором).
        
        Используется в случае проблем с замком или когда клиент забыл закрыть.
        """
        locker = self.locker_repo.get_by_number(locker_number)
        if not locker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шкафчик не найден"
            )
        
        active_session = self.session_repo.get_active_by_locker(locker.id)
        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шкафчик не занят"
            )
        
        # Отправляем команду на открытие замка (если ONLINE)
        if locker.lock_type == LockType.ONLINE.value and locker.device_id:
            self._send_lock_command(locker.device_id, "OPEN")
        
        # Закрываем сессию
        active_session.status = LockerSessionStatus.CLOSED.value
        active_session.ended_at = datetime.now()
        active_session.notes = f"Принудительно освобождён администратором. Причина: {reason}"
        
        # Обновляем статус шкафчика
        locker.status = LockerStatus.FREE.value
        
        self.db.commit()
        
        self.audit.log(
            action="locker.force_release",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker_number} force released by admin. Reason: {reason}",
        )
        
        return {
            "success": True,
            "locker_number": locker.number,
            "message": f"Шкафчик №{locker_number} принудительно освобождён",
        }