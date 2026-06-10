# app\api\v1\client_history.py

# app/api/v1/client_history.py

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.client_event import ClientEventListResponse
from app.services.client_history_service import ClientHistoryService

# создаём роутер истории клиента
router = APIRouter(prefix="/clients", tags=["Client History"])


# ============================================================
# Получить timeline клиента
# ============================================================
@router.get("/{client_id}/timeline", response_model=ClientEventListResponse)
def get_client_timeline(
    # UUID клиента из URL
    client_id: UUID,

    # лимит элементов
    limit: int = Query(default=100, ge=1, le=300),

    # смещение для пагинации
    offset: int = Query(default=0, ge=0),

    # проверяем право чтения клиентов
    current_user=Depends(require_permission("clients.read")),

    # получаем сессию БД
    db: Session = Depends(get_db),
):
    # создаём сервис истории
    history_service = ClientHistoryService(db)

    # возвращаем timeline
    return history_service.get_client_timeline(
        client_id=str(client_id),
        limit=limit,
        offset=offset,
    )