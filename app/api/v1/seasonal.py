"""E39: Сезонные кампании (ТЗ v3.2 §4.14).

Сезонные акции (зима/весна/лето/осень/НГ), промокоды с валидацией
по датам и статусу, автоактивация/завершение по календарю,
статистика применений.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/seasonal", tags=["seasonal"])

_FMT = "%Y-%m-%d %H:%M:%S"
_SEASONS = ("winter", "spring", "summer", "autumn", "new_year", "custom")


def _now():
    return datetime.now()


def _fmt(dt):
    return dt.strftime(_FMT)


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _insert(db, table, data):
    cols = _cols(db, table)
    d = {k: v for k, v in data.items() if k in cols}
    names = ", ".join(d.keys())
    params = ", ".join(":" + k for k in d.keys())
    db.execute(text(f"INSERT INTO {table} ({names}) VALUES ({params})"), d)


def _get_campaign(db, campaign_id):
    row = db.execute(
        text("SELECT * FROM seasonal_campaigns WHERE id=:i"), {"i": campaign_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    return dict(row)


def _validate_dates(start, end):
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="Некорректные даты: начало позже окончания")


def _check_usable(camp):
    if camp["status"] != "active":
        raise HTTPException(status_code=400, detail="Акция не активна")
    today = _today()
    if camp.get("start_date") and today < camp["start_date"]:
        raise HTTPException(status_code=400, detail="Акция ещё не началась")
    if camp.get("end_date") and today > camp["end_date"]:
        raise HTTPException(status_code=400, detail="Срок акции истёк")


class CampaignCreate(BaseModel):
    name: str
    season: str = "custom"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    discount_percent: float = 0
    promo_code: Optional[str] = None
    auto_activate: bool = False


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    discount_percent: Optional[float] = None


class PromoRequest(BaseModel):
    promo_code: str
    client_id: str
    amount: float


@router.post("/campaigns", status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    if payload.season not in _SEASONS:
        raise HTTPException(status_code=400, detail="Неизвестный сезон")
    _validate_dates(payload.start_date, payload.end_date)
    if payload.discount_percent < 0 or payload.discount_percent > 100:
        raise HTTPException(status_code=400, detail="Некорректная скидка")
    promo = payload.promo_code or ("SALE-" + uuid.uuid4().hex[:6].upper())
    dup = db.execute(
        text("SELECT id FROM seasonal_campaigns WHERE promo_code=:p"), {"p": promo}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Промокод уже существует")
    cid = str(uuid.uuid4())
    _insert(db, "seasonal_campaigns", {
        "id": cid, "name": payload.name, "season": payload.season,
        "start_date": payload.start_date, "end_date": payload.end_date,
        "discount_percent": payload.discount_percent, "promo_code": promo,
        "status": "draft", "auto_activate": 1 if payload.auto_activate else 0,
        "created_at": _fmt(_now()),
    })
    db.commit()
    return {"campaign_id": cid, "promo_code": promo, "status": "draft", "message": "Кампания создана"}


@router.get("/campaigns")
def list_campaigns(season: Optional[str] = Query(None), status: Optional[str] = Query(None),
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM seasonal_campaigns WHERE 1=1"
    params = {}
    if season:
        q += " AND season=:s"
        params["s"] = season
    if status:
        q += " AND status=:st"
        params["st"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_campaign(db, campaign_id)


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, payload: CampaignUpdate,
                    db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_campaign(db, campaign_id)
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "start_date" in fields or "end_date" in fields:
        _validate_dates(fields.get("start_date"), fields.get("end_date"))
    if "discount_percent" in fields and (fields["discount_percent"] < 0 or fields["discount_percent"] > 100):
        raise HTTPException(status_code=400, detail="Некорректная скидка")
    if fields:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        fields["cid"] = campaign_id
        db.execute(text(f"UPDATE seasonal_campaigns SET {sets} WHERE id=:cid"), fields)
        db.commit()
    return {"message": "Кампания обновлена"}


@router.post("/campaigns/{campaign_id}/activate")
def activate_campaign(campaign_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    camp = _get_campaign(db, campaign_id)
    if camp["status"] == "active":
        raise HTTPException(status_code=400, detail="Кампания уже активирована")
    if camp["status"] == "finished":
        raise HTTPException(status_code=400, detail="Кампания завершена")
    db.execute(text("UPDATE seasonal_campaigns SET status='active' WHERE id=:i"), {"i": campaign_id})
    db.commit()
    return {"message": "Кампания активирована", "status": "active"}


@router.post("/campaigns/{campaign_id}/finish")
def finish_campaign(campaign_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    camp = _get_campaign(db, campaign_id)
    if camp["status"] != "active":
        raise HTTPException(status_code=400, detail="Кампания не активна")
    db.execute(text("UPDATE seasonal_campaigns SET status='finished' WHERE id=:i"), {"i": campaign_id})
    db.commit()
    return {"message": "Кампания завершена", "status": "finished"}


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_campaign(db, campaign_id)
    db.execute(text("DELETE FROM seasonal_promo_uses WHERE campaign_id=:i"), {"i": campaign_id})
    db.execute(text("DELETE FROM seasonal_campaigns WHERE id=:i"), {"i": campaign_id})
    db.commit()
    return None


@router.get("/campaigns/{campaign_id}/stats")
def campaign_stats(campaign_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_campaign(db, campaign_id)
    uses = db.execute(
        text("SELECT COUNT(*) FROM seasonal_promo_uses WHERE campaign_id=:i"), {"i": campaign_id}
    ).scalar()
    discount = db.execute(
        text("SELECT COALESCE(SUM(discount_applied),0) FROM seasonal_promo_uses WHERE campaign_id=:i"), {"i": campaign_id}
    ).scalar()
    revenue = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM seasonal_promo_uses WHERE campaign_id=:i"), {"i": campaign_id}
    ).scalar()
    return {"campaign_id": campaign_id, "uses": uses,
            "discount_total": float(discount or 0), "revenue_total": float(revenue or 0)}


@router.post("/promo/validate")
def promo_validate(payload: PromoRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM seasonal_campaigns WHERE promo_code=:p"), {"p": payload.promo_code}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    camp = dict(row)
    _check_usable(camp)
    disc = round(payload.amount * (camp["discount_percent"] or 0) / 100.0, 2)
    return {"valid": True, "campaign_id": camp["id"], "discount_percent": camp["discount_percent"],
            "discount": disc, "final_amount": round(payload.amount - disc, 2)}


@router.post("/promo/apply", status_code=201)
def promo_apply(payload: PromoRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM seasonal_campaigns WHERE promo_code=:p"), {"p": payload.promo_code}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    camp = dict(row)
    _check_usable(camp)
    dup = db.execute(
        text("SELECT id FROM seasonal_promo_uses WHERE campaign_id=:c AND client_id=:cl"),
        {"c": camp["id"], "cl": payload.client_id},
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Промокод уже использован этим клиентом")
    disc = round(payload.amount * (camp["discount_percent"] or 0) / 100.0, 2)
    _insert(db, "seasonal_promo_uses", {
        "id": str(uuid.uuid4()), "campaign_id": camp["id"], "client_id": payload.client_id,
        "amount": payload.amount, "discount_applied": disc, "used_at": _fmt(_now()),
    })
    db.commit()
    return {"applied": True, "discount": disc, "final_amount": round(payload.amount - disc, 2),
            "message": "Промокод применён"}


@router.post("/auto-activate")
def auto_activate(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    today = _today()
    r1 = db.execute(
        text("UPDATE seasonal_campaigns SET status='active' WHERE status='draft' AND auto_activate=1 AND start_date IS NOT NULL AND start_date<=:t"),
        {"t": today},
    )
    r2 = db.execute(
        text("UPDATE seasonal_campaigns SET status='finished' WHERE status='active' AND end_date IS NOT NULL AND end_date<:t"),
        {"t": today},
    )
    db.commit()
    return {"activated": r1.rowcount, "finished": r2.rowcount,
            "message": "Автоактивация выполнена"}
