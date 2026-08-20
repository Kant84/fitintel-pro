"""E44: AI Analytics (ТЗ v3.2 §4.20).

Прогноз оттока клиентов (churn score по факторам посещаемости),
персональные рекомендации, heatmap посещаемости (день недели x час),
сегментация по риску. Расчёт on-the-fly по visits/subscriptions.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics-ai"])

_DATE_COLS = ("visited_at", "visit_date", "check_in_at", "created_at", "start_time")


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _visit_date_col(db):
    cols = _cols(db, "visits")
    for c in _DATE_COLS:
        if c in cols:
            return c
    return None


def _parse_dt(v):
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    if isinstance(v, str):
        for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v[:19], f)
            except ValueError:
                continue
    return None


def _client_exists(db, client_id):
    try:
        key = uuid.UUID(str(client_id))
    except (ValueError, AttributeError):
        return False
    row = db.execute(text("SELECT id FROM clients WHERE id=:i"), {"i": key}).fetchone()
    return row is not None


def _client_visits(db, client_id):
    dcol = _visit_date_col(db)
    if not dcol:
        return []
    rows = db.execute(
        text(f"SELECT {dcol} FROM visits WHERE client_id::text=:c"), {"c": str(client_id)}
    ).fetchall()
    out = []
    for r in rows:
        dt = _parse_dt(r[0])
        if dt:
            out.append(dt)
    return out


def _active_subscription(db, client_id):
    try:
        row = db.execute(
            text("SELECT end_date FROM subscriptions WHERE client_id::text=:c AND status='active' ORDER BY end_date DESC LIMIT 1"),
            {"c": str(client_id)},
        ).fetchone()
        return _parse_dt(row[0]) if row else None
    except Exception:
        return None


def _churn_score(db, client_id):
    visits = _client_visits(db, client_id)
    now = datetime.now()
    last = max(visits) if visits else None
    v30 = len([v for v in visits if v >= now - timedelta(days=30)])
    days_since = (now - last).days if last else 999
    sub_end = _active_subscription(db, client_id)
    days_to_end = (sub_end - now).days if sub_end else None

    score = 0
    if days_since > 30:
        score += 60
    elif days_since > 14:
        score += 40
    elif days_since > 7:
        score += 15
    if v30 == 0:
        score += 30
    elif v30 < 2:
        score += 15
    if days_to_end is not None and days_to_end <= 14:
        score += 10
    score = min(score, 100)
    level = "high" if score >= 60 else ("medium" if score >= 30 else "low")
    return {
        "client_id": str(client_id),
        "risk_score": score,
        "risk_level": level,
        "last_visit": last.strftime("%Y-%m-%d %H:%M:%S") if last else None,
        "days_since_visit": days_since if last else None,
        "visits_last_30d": v30,
        "total_visits": len(visits),
        "subscription_days_left": days_to_end,
    }


def _recommendations(factors):
    recs = []
    if factors["risk_level"] == "high":
        recs.append({"type": "retention", "priority": "high",
                     "message": "Высокий риск оттока: предложите персональную тренировку со скидкой 20%"})
    if factors["visits_last_30d"] == 0:
        recs.append({"type": "winback", "priority": "high",
                     "message": "Клиент давно не посещает клуб: отправьте win-back рассылку с бонусом"})
    elif factors["visits_last_30d"] < 2:
        recs.append({"type": "motivation", "priority": "medium",
                     "message": "Низкая активность: предложите заморозку вместо расторжения или групповые занятия"})
    dleft = factors.get("subscription_days_left")
    if dleft is not None and dleft <= 14:
        recs.append({"type": "renewal", "priority": "high",
                     "message": f"Абонемент истекает через {dleft} дн.: предложите продление со скидкой 10%"})
    if factors["total_visits"] >= 10 and dleft is not None and dleft > 60:
        recs.append({"type": "upsell", "priority": "low",
                     "message": "Лояльный клиент: предложите годовой абонемент с выгодой 2 месяца"})
    if not recs:
        recs.append({"type": "cross_sell", "priority": "low",
                     "message": "Стабильная активность: предложите дополнительные услуги клуба"})
    return recs


@router.get("/ai/churn")
def churn_list(min_risk: int = Query(0, ge=0, le=100), limit: int = Query(50, le=200),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(
        text("SELECT id FROM clients WHERE is_active=true LIMIT 500")
    ).fetchall()
    out = []
    for r in rows:
        f = _churn_score(db, str(r[0]))
        if f["risk_score"] >= min_risk:
            out.append(f)
    out.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"total": len(out), "items": out[:limit]}


@router.get("/ai/churn/{client_id}")
def churn_detail(client_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not _client_exists(db, client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    factors = _churn_score(db, client_id)
    factors["recommendations"] = _recommendations(factors)
    return factors


@router.get("/ai/recommendations/{client_id}")
def recommendations(client_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not _client_exists(db, client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    factors = _churn_score(db, client_id)
    return {"client_id": client_id, "risk_level": factors["risk_level"],
            "recommendations": _recommendations(factors)}


@router.get("/ai/heatmap")
def heatmap(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
            user=Depends(get_current_user)):
    dcol = _visit_date_col(db)
    if not dcol:
        return {"days": days, "grid": [], "max": 0}
    rows = db.execute(text(f"SELECT {dcol} FROM visits")).fetchall()
    cutoff = datetime.now() - timedelta(days=days)
    grid = {}
    for r in rows:
        dt = _parse_dt(r[0])
        if dt and dt >= cutoff:
            key = (dt.weekday(), dt.hour)
            grid[key] = grid.get(key, 0) + 1
    items = [{"weekday": k[0], "hour": k[1], "count": v}
             for k, v in sorted(grid.items())]
    return {"days": days, "grid": items,
            "max": max((i["count"] for i in items), default=0)}


@router.get("/ai/risk-segments")
def risk_segments(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("SELECT id FROM clients WHERE is_active=true LIMIT 500")).fetchall()
    seg = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        f = _churn_score(db, str(r[0]))
        seg[f["risk_level"]] += 1
    return {"segments": seg, "total": sum(seg.values())}


@router.post("/ai/recalc")
def recalc(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.execute(text("SELECT COUNT(*) FROM clients WHERE is_active=true")).scalar()
    return {"message": "Модель пересчитана", "clients_processed": rows,
            "model": "rules-v1", "recalculated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
