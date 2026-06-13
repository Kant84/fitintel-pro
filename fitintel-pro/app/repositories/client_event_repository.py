# app/repositories/client_event_repository.py

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.client_event import ClientEvent


class ClientEventRepository:
    """Репозиторий для работы с событиями клиента"""
    
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, event: ClientEvent) -> ClientEvent:
        """Добавить событие клиента"""
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_by_client_id(
        self, 
        client_id: str, 
        limit: int = 100,
        offset: int = 0,
    ) -> list[ClientEvent]:
        """Получить список событий клиента по ID"""
        stmt = (
            select(ClientEvent)
            .where(ClientEvent.client_id == client_id)
            .order_by(ClientEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def count_by_client_id(self, client_id: str) -> int:
        """Получить количество событий клиента"""
        stmt = (
            select(ClientEvent)
            .where(ClientEvent.client_id == client_id)
        )
        result = self.db.execute(stmt)
        return len(list(result.scalars().all()))