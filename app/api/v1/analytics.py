# app/api/v1/analytics.py
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard(
    club_id: str | None = Query(default=None),
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Ключевые метрики дашборда"""
    from app.models.client import Client
    from app.models.visit import Visit
    from app.models.subscription import Subscription
    from app.models.payment import Payment

    today = date.today()
    first_day = today.replace(day=1)

    total_clients = db.query(func.count(Client.id)).scalar() or 0
    active_clients = db.query(func.count(Client.id)).filter(Client.is_active == True).scalar() or 0

    visits_today = db.query(func.count(Visit.id)).filter(
        func.date(Visit.entry_time) == today
    ).scalar() or 0

    active_subscriptions = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "ACTIVE"
    ).scalar() or 0

    revenue_month = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "COMPLETED",
        func.date(Payment.created_at) >= first_day
    ).scalar() or 0

    return {
        "period": f"{first_day} - {today}",
        "clients": {"total": total_clients, "active": active_clients},
        "visits_today": visits_today,
        "subscriptions_active": active_subscriptions,
        "revenue_month": float(revenue_month),
    }


@router.get("/visits")
def visits_analytics(
    start: date = Query(...),
    end: date = Query(...),
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Аналитика посещений за период"""
    result = db.execute(text("""
        SELECT 
            date_trunc('day', entry_time)::date as day,
            count(*) as visits,
            count(distinct client_id) as unique_clients
        FROM visits
        WHERE entry_time BETWEEN :start AND :end
        GROUP BY 1
        ORDER BY 1
    """), {"start": start, "end": end})

    rows = result.mappings().all()
    return {
        "period": {"start": str(start), "end": str(end)},
        "daily": [{"day": str(r["day"]), "visits": r["visits"], "unique_clients": r["unique_clients"]} for r in rows],
        "total_visits": sum(r["visits"] for r in rows),
    }


@router.get("/finance")
def finance_analytics(
    start: date = Query(...),
    end: date = Query(...),
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Финансовая аналитика за период"""
    result = db.execute(text("""
        SELECT 
            status,
            count(*) as count,
            coalesce(sum(amount), 0) as total
        FROM payments
        WHERE created_at BETWEEN :start AND :end
        GROUP BY status
    """), {"start": start, "end": end})

    rows = result.mappings().all()
    return {
        "period": {"start": str(start), "end": str(end)},
        "by_status": [{"status": r["status"], "count": r["count"], "total": float(r["total"])} for r in rows],
    }


@router.get("/clients/retention")
def client_retention(
    current_user=Depends(require_permission("analytics.read")),
    db: Session = Depends(get_db),
):
    """Retention клиентов — когортный анализ"""
    result = db.execute(text("""
        WITH first_visit AS (
            SELECT client_id, min(date_trunc('month', entry_time))::date as cohort
            FROM visits
            GROUP BY client_id
        )
        SELECT 
            cohort,
            count(*) as total,
            count(distinct client_id) as retained
        FROM first_visit
        GROUP BY cohort
        ORDER BY cohort DESC
        LIMIT 12
    """))

    rows = result.mappings().all()
    return {
        "cohorts": [{"month": str(r["cohort"]), "total": r["total"], "retained": r["retained"],
                     "retention_rate": round(r["retained"] / max(r["total"], 1) * 100, 1)} for r in rows]
    }
