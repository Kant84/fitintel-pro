# app/repositories/access_repository.py

from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.models.access_log import AccessLog
from app.models.credential import Credential


class AccessRepository:
    """Репозиторий логов доступа и проверок СКУД"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # === Access Logs ===

    def create_log(self, log: AccessLog) -> AccessLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_log_by_id(self, log_id: UUID) -> AccessLog | None:
        return self.db.execute(
            select(AccessLog).where(AccessLog.id == log_id)
        ).scalar_one_or_none()

    def list_logs(
        self,
        offset: int = 0,
        limit: int = 100,
        client_id: UUID | None = None,
        status: str | None = None,
        device_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AccessLog], int]:
        query = select(AccessLog)
        if client_id:
            query = query.where(AccessLog.client_id == client_id)
        if status:
            query = query.where(AccessLog.status == status)
        if device_id:
            query = query.where(AccessLog.device_id == device_id)
        if date_from:
            query = query.where(AccessLog.created_at >= date_from)
        if date_to:
            query = query.where(AccessLog.created_at <= date_to)
        query = query.order_by(desc(AccessLog.created_at))

        all_logs = list(self.db.execute(query).scalars().all())
        return all_logs[offset:offset + limit], len(all_logs)

    def get_last_client_access(self, client_id: UUID) -> AccessLog | None:
        """Последняя запись доступа клиента"""
        return self.db.execute(
            select(AccessLog)
            .where(AccessLog.client_id == client_id)
            .order_by(desc(AccessLog.created_at))
        ).scalars().first()

    def count_access_today(self, client_id: UUID) -> int:
        """Количество проходов клиента сегодня"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.db.execute(
            select(func.count(AccessLog.id))
            .where(AccessLog.client_id == client_id)
            .where(AccessLog.created_at >= today)
            .where(AccessLog.direction == "entry")
        ).scalar() or 0

    def get_current_in_gym(self) -> list[AccessLog]:
        """Кто сейчас в зале (вошёл, не вышел)"""
        # Подзапрос: последняя запись для каждого клиента
        from sqlalchemy import and_
        subq = (
            select(
                AccessLog.client_id,
                func.max(AccessLog.created_at).label("last_access")
            )
            .group_by(AccessLog.client_id)
            .subquery()
        )
        return list(self.db.execute(
            select(AccessLog)
            .join(subq, and_(
                AccessLog.client_id == subq.c.client_id,
                AccessLog.created_at == subq.c.last_access
            ))
            .where(AccessLog.direction == "entry")
            .order_by(desc(AccessLog.created_at))
        ).scalars().all())

    # === Credential checks ===

    def get_credential_by_code(self, code: str) -> Credential | None:
        return self.db.execute(
            select(Credential).where(Credential.code == code)
        ).scalar_one_or_none()

    def get_active_client_credentials(self, client_id: UUID) -> list[Credential]:
        return list(self.db.execute(
            select(Credential)
            .where(Credential.client_id == client_id)
            .where(Credential.is_active == True)
            .where(Credential.is_blocked == False)
        ).scalars().all())
