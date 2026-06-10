# app/services/client_history_service.py

from sqlalchemy.orm import Session
from app.models.client_event import ClientEvent
from app.repositories.client_event_repository import ClientEventRepository
from app.schemas.client_event import (
    ClientEventResponse,
    ClientEventListResponse,
)


class ClientHistoryService:
    """Сервис для работы с историей клиента (timeline)"""
    
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ClientEventRepository(db)

    def add_event(
        self,
        *,
        client_id: str,
        event_type: str,
        title: str,
        description: str | None = None,
        actor_user_id: str | None = None,
    ) -> ClientEvent:
        """Добавить событие в историю клиента"""
        event = ClientEvent(
            client_id=client_id,
            event_type=event_type,
            title=title,
            description=description,
            actor_user_id=actor_user_id,
        )
        return self.repo.add(event)
        print(f"🔍 DEBUG: add_event called: client_id={client_id}, event_type={event_type}")
        
    def get_client_timeline(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> ClientEventListResponse:
        """Получить timeline клиента"""
        events = self.repo.list_by_client_id(
            client_id=client_id,
            limit=limit,
            offset=offset,
        )
        return ClientEventListResponse(
            items=[ClientEventResponse.model_validate(e) for e in events],
            count=len(events),
        )