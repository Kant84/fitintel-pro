"""E60: Auto-Scheduler API — запуск автоматики одной кнопкой."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.ml.auto_scheduler import AutoScheduler

router = APIRouter(prefix="/auto", tags=["Auto / Self-Learning"])

@router.post("/run-daily")
def run_daily_auto(db: Session = Depends(get_db)):
    """
    Запустить все автоматические задачи за день.
    Сотруднику не нужно ничего делать — система сама найдёт кого напомнить.
    """
    scheduler = AutoScheduler(db)
    results = scheduler.run_daily()
    return {
        "status": "completed",
        "notifications_created": sum(results.values()),
        "breakdown": results,
        "message": "Автоматика выполнена. Проверьте вкладку Уведомления."
    }

@router.get("/stats")
def get_auto_stats(db: Session = Depends(get_db)):
    """Статистика автоматических задач."""
    from sqlalchemy import text
    sql = text("SELECT type, COUNT(*) FROM notifications WHERE created_at > NOW() - INTERVAL '7 days' GROUP BY type")
    rows = db.execute(sql).fetchall()
    return {"last_7_days": {r[0]: r[1] for r in rows}}
