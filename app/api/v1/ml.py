"""E60: ML API — предсказания, аналитика, оптимизация."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.ml.churn_model import ChurnModel
from app.ml.event_logger import EventLogger

router = APIRouter(prefix="/ml", tags=["ML / Self-Learning"])

@router.get("/predict/churn")
def predict_churn(
    client_id: str = Query(..., description="UUID клиента"),
    db: Session = Depends(get_db),
):
    """Предсказать вероятность оттока клиента."""
    model = ChurnModel(db)
    result = model.predict(client_id)
    return result

@router.post("/predict/churn/batch")
def predict_churn_batch(
    client_ids: List[str],
    db: Session = Depends(get_db),
):
    """Предсказать отток для списка клиентов."""
    model = ChurnModel(db)
    return model.batch_predict(client_ids)

@router.get("/features/client")
def get_client_features(
    client_id: str = Query(..., description="UUID клиента"),
    db: Session = Depends(get_db),
):
    """Получить признаки клиента для ML."""
    from app.ml.feature_store import FeatureStore
    store = FeatureStore(db)
    return store.get_client_features(client_id)

@router.get("/events/recent")
def get_recent_events(
    limit: int = Query(50, ge=1, le=500),
    event_type: str = Query(None, description="Фильтр по типу события"),
    db: Session = Depends(get_db),
):
    """Последние события из ml_events."""
    from sqlalchemy import text
    if event_type:
        sql = text("SELECT * FROM ml_events WHERE event_type = :type ORDER BY created_at DESC LIMIT :limit")
        result = db.execute(sql, {"type": event_type, "limit": limit})
    else:
        sql = text("SELECT * FROM ml_events ORDER BY created_at DESC LIMIT :limit")
        result = db.execute(sql, {"limit": limit})
    events = []
    for row in result:
        events.append({
            "id": str(row[0]),
            "event_type": row[1],
            "payload": row[2],
            "client_id": str(row[3]) if row[3] else None,
            "created_at": str(row[7]),
        })
    return {"count": len(events), "events": events}
