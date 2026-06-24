# app/services/locker_service.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.locker import Locker
from app.models.locker_session import LockerSession
from app.models.client import Client
from app.services.audit_service import AuditService


class LockerService:
    """Сервис управления шкафчиками (E11)"""

    def __init__(self, db: Session):
        self.db = db

    def create_locker(
        self,
        number: str,
        zone: str | None = None,
        lock_type: str = "OFFLINE",
        device_id: str | None = None,
        requires_privilege: bool = False,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Locker:
        """Создать шкафчик (E11.1)"""
        # Проверяем уникальность номера (E11.2)
        existing = self.db.query(Locker).filter(Locker.number == number).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Шкафчик с таким номером уже существует",
            )

        locker = Locker(
            number=number,
            zone=zone,
            lock_type=lock_type,
            device_id=device_id,
            requires_privilege=requires_privilege,
            notes=notes,
        )
        self.db.add(locker)
        self.db.commit()
        self.db.refresh(locker)

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {number} created",
            after_data={"number": number, "zone": zone, "lock_type": lock_type},
        )

        return locker

    def get_locker(self, locker_id: str) -> Locker:
        """Получить шкафчик по ID"""
        locker = self.db.query(Locker).filter(Locker.id == locker_id).first()
        if not locker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шкафчик не найден",
            )
        return locker

    def list_lockers(self) -> list[Locker]:
        """Получить список шкафчиков (E11.3)"""
        return self.db.query(Locker).order_by(Locker.number).all()

    def assign_locker(
        self,
        locker_id: str,
        client_id: str,
        credential_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> LockerSession:
        """Выдать шкафчик клиенту (E11.4)"""
        locker = self.get_locker(locker_id)

        # Проверяем, что шкафчик свободен (E11.5)
        if locker.status != "FREE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Шкафчик занят",
            )

        # Проверяем клиента
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        # Создаём сессию
        session = LockerSession(
            locker_id=locker.id,
            client_id=client.id,
            credential_id=credential_id,
            lock_type=locker.lock_type,
            status="ACTIVE",
        )
        self.db.add(session)

        # Обновляем статус шкафчика
        locker.status = "OCCUPIED"
        locker.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.assigned",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker.number} assigned to client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(client.id),
                "session_id": str(session.id),
                "lock_type": locker.lock_type,
            },
        )

        return session

    def release_locker(
        self,
        locker_id: str,
        actor_user_id: str | None = None,
    ) -> Locker:
        """Освободить шкафчик (E11.6)"""
        locker = self.get_locker(locker_id)

        # Проверяем, что шкафчик занят (E11.7)
        if locker.status != "OCCUPIED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шкафчик уже свободен",
            )

        # Закрываем активную сессию
        session = (
            self.db.query(LockerSession)
            .filter(LockerSession.locker_id == locker_id, LockerSession.status == "ACTIVE")
            .first()
        )
        if session:
            session.status = "COMPLETED"
            session.ended_at = datetime.now(timezone.utc)
            session.updated_at = datetime.now(timezone.utc)

        # Обновляем статус шкафчика
        locker.status = "FREE"
        locker.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(locker)

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.released",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker.number} released",
        )

        return locker

    def block_locker(
        self,
        locker_id: str,
        reason: str,
        actor_user_id: str | None = None,
    ) -> Locker:
        """Заблокировать шкафчик (E11.8)"""
        locker = self.get_locker(locker_id)

        locker.status = "BLOCKED"
        locker.notes = reason
        locker.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(locker)

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.blocked",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker.number} blocked: {reason}",
            after_data={"reason": reason},
        )

        return locker

    def get_locker_status(self, locker_id: str) -> dict:
        """Получить статус шкафчика (E11.9)"""
        locker = self.get_locker(locker_id)

        result = {
            "id": locker.id,
            "number": locker.number,
            "status": locker.status,
            "client_id": None,
            "client_name": None,
            "session_id": None,
            "lock_status": None,
        }

        if locker.status == "OCCUPIED":
            session = (
                self.db.query(LockerSession)
                .filter(LockerSession.locker_id == locker_id, LockerSession.status == "ACTIVE")
                .first()
            )
            if session:
                client = self.db.query(Client).filter(Client.id == session.client_id).first()
                result["client_id"] = session.client_id
                result["client_name"] = f"{client.first_name} {client.last_name}" if client else None
                result["session_id"] = session.id

        return result

    def delete_locker(
        self,
        locker_id: str,
        actor_user_id: str | None = None,
    ) -> None:
        """Удалить шкафчик (E11.11)"""
        locker = self.get_locker(locker_id)

        # Проверяем, что шкафчик не занят (E11.12)
        if locker.status == "OCCUPIED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя удалить занятый шкафчик",
            )

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.deleted",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="locker",
            entity_id=locker.id,
            message=f"Locker {locker.number} deleted",
            before_data={"number": locker.number, "status": locker.status},
        )

        self.db.delete(locker)
        self.db.commit()

    def open_locker(
        self,
        locker_id: str,
        actor_user_id: str | None = None,
    ) -> dict:
        """Открыть замок шкафчика (E11.13)"""
        from app.hardware.manager import DeviceManager
        from app.hardware.base import AccessResult

        locker = self.get_locker(locker_id)

        # Проверяем, что шкафчик не заблокирован
        if locker.status == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шкафчик заблокирован",
            )

        # Открываем через Hardware Manager
        if locker.device_id:
            device = DeviceManager.get_device(locker.device_id)
            if device:
                try:
                    import asyncio
                    result = asyncio.run(DeviceManager.open_device(locker.device_id))
                    if result == AccessResult.GRANTED:
                        return {
                            "success": True,
                            "locker_id": locker.id,
                            "message": "Замок открыт",
                            "lock_status": "open",
                        }
                    else:
                        return {
                            "success": False,
                            "locker_id": locker.id,
                            "message": "Не удалось открыть замок",
                            "lock_status": "closed",
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "locker_id": locker.id,
                        "message": f"Ошибка связи: {e}",
                        "lock_status": "offline",
                    }
            else:
                # E11.14: Устройство недоступно
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Устройство недоступно",
                )

        # OFFLINE замок — просто возвращаем success
        return {
            "success": True,
            "locker_id": locker.id,
            "message": "Замок открыт (OFFLINE)",
            "lock_status": "open",
        }

    def auto_release_on_checkout(self, client_id: str) -> bool:
        """Авто-освобождение при выходе клиента (E11.10)"""
        # Находим активную сессию клиента
        session = (
            self.db.query(LockerSession)
            .filter(LockerSession.client_id == client_id, LockerSession.status == "ACTIVE")
            .first()
        )
        if not session:
            return False

        # Закрываем сессию
        session.status = "COMPLETED"
        session.ended_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)

        # Освобождаем шкафчик
        locker = self.db.query(Locker).filter(Locker.id == session.locker_id).first()
        if locker:
            locker.status = "FREE"
            locker.updated_at = datetime.now(timezone.utc)

        self.db.commit()

        # Audit
        audit = AuditService(self.db)
        audit.log(
            action="lockers.auto_released",
            status="success",
            entity_type="locker",
            entity_id=locker.id if locker else None,
            message=f"Locker auto-released on client checkout",
            after_data={"client_id": str(client_id), "session_id": str(session.id)},
        )

        return True
