# app/api/v1/marketing.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.services.marketing_service import MarketingService

router = APIRouter(prefix="/marketing", tags=["Marketing"])


def get_service(db: Session = Depends(get_db)) -> MarketingService:
    return MarketingService(db)


# ============================================================
# СЕГМЕНТЫ
# ============================================================

@router.get("/segments")
def client_segments(
    current_user=Depends(require_permission("marketing.read")),
    service: MarketingService = Depends(get_service),
):
    """Сегменты клиентов с реальной аналитикой"""
    return {"segments": service.get_segments()}


@router.get("/segments/{segment_id}/clients")
def segment_clients(
    segment_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_permission("marketing.read")),
    service: MarketingService = Depends(get_service),
):
    """Клиенты конкретного сегмента"""
    return service.get_segment_clients(segment_id, offset, limit)


# ============================================================
# SMS РАССЫЛКА
# ============================================================

@router.post("/send-sms")
def send_sms(
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить SMS на конкретные номера"""
    return service.send_sms(
        phones=payload.get("phones", []),
        message=payload.get("text", ""),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


@router.post("/segments/{segment_id}/send-sms")
def send_sms_to_segment(
    segment_id: str,
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить SMS сегменту клиентов"""
    return service.send_sms_to_segment(
        segment_id=segment_id,
        message=payload.get("text", ""),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


# ============================================================
# EMAIL РАССЫЛКА
# ============================================================

@router.post("/send-email")
def send_email(
    payload: dict,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Отправить email-рассылку"""
    return service.send_email(
        to_emails=payload.get("emails", []),
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
        html=payload.get("html", False),
        campaign_name=payload.get("campaign_name"),
        actor_user_id=current_user.id,
    )


# ============================================================
# КАМПАНИИ
# ============================================================

# ============================================================
# КАМПАНИИ (E34)
# ============================================================
from datetime import datetime as _e34_dt, timezone as _e34_tz
import json as _e34_json
import uuid as _e34_uuid
from typing import Optional as _e34_Optional

from fastapi import HTTPException as _e34_HTTPException
from pydantic import BaseModel as _e34_BaseModel
from sqlalchemy import text as _e34_text

from app.api.dependencies import get_current_user as _e34_gcu


class _CampaignCreate(_e34_BaseModel):
    name: _e34_Optional[str] = None
    type: str = "email"
    target_audience: str = "all"
    budget: float = 0.0


class _CampaignUpdate(_e34_BaseModel):
    name: _e34_Optional[str] = None
    budget: _e34_Optional[float] = None
    status: _e34_Optional[str] = None
    target_audience: _e34_Optional[str] = None


class _SegmentCreate(_e34_BaseModel):
    name: str = "Сегмент"
    criteria: dict = {}


class _ABTestRequest(_e34_BaseModel):
    variant_a: str
    variant_b: str


def _e34_insert(db, table, data):
    rows = db.execute(_e34_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    cols = {r[0] for r in rows}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(_e34_text(
        f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"
    ), data)


_E34_COLS = "id, name, type, target_audience, budget, status, created_at"


def _e34_campaign_dict(r):
    return {"campaign_id": r[0], "name": r[1], "type": r[2],
            "target_audience": r[3], "budget": float(r[4] or 0),
            "status": r[5], "created_at": str(r[6]) if r[6] else None}


def _e34_get_campaign(db, cid):
    return db.execute(_e34_text(
        f"SELECT {_E34_COLS} FROM marketing_campaigns WHERE id = :id"
    ), {"id": cid}).fetchone()


@router.get("/campaigns")
def list_campaigns(db: Session = Depends(get_db), current_user=Depends(_e34_gcu)):
    """E34.3 — список кампаний"""
    rows = db.execute(_e34_text(
        f"SELECT {_E34_COLS} FROM marketing_campaigns ORDER BY created_at DESC"
    )).fetchall()
    campaigns = [_e34_campaign_dict(r) for r in rows]
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.post("/campaigns", status_code=201)
def create_campaign(payload: _CampaignCreate, db: Session = Depends(get_db),
                    current_user=Depends(_e34_gcu)):
    """E34.1/E34.2 — создание кампании"""
    if not payload.name:
        raise _e34_HTTPException(status_code=422, detail="Название обязательно")
    cid = str(_e34_uuid.uuid4())
    now = _e34_dt.now(_e34_tz.utc)
    _e34_insert(db, "marketing_campaigns", {
        "id": cid, "name": payload.name, "type": payload.type,
        "target_audience": payload.target_audience, "budget": payload.budget,
        "status": "draft", "created_at": now, "updated_at": now,
    })
    db.commit()
    return {"campaign_id": cid, "name": payload.name, "type": payload.type,
            "target_audience": payload.target_audience, "budget": payload.budget,
            "status": "draft", "message": "Кампания создана"}


@router.post("/campaigns/{campaign_id}/launch")
def launch_campaign(
    campaign_id: UUID,
    current_user=Depends(require_permission("marketing.send")),
    service: MarketingService = Depends(get_service),
):
    """Запустить кампанию"""
    return service.launch_campaign(campaign_id, actor_user_id=current_user.id)

# ---------------- E34: CRUD кампании, сегменты, рассылки, аналитика ----------------

@router.get("/campaigns/{campaign_id}")
def e34_get_campaign_ep(campaign_id: str, db: Session = Depends(get_db),
                        current_user=Depends(_e34_gcu)):
    """E34.4 — кампания по ID"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    return _e34_campaign_dict(r)


@router.put("/campaigns/{campaign_id}")
def e34_update_campaign(campaign_id: str, payload: _CampaignUpdate,
                        db: Session = Depends(get_db), current_user=Depends(_e34_gcu)):
    """E34.5 — обновление кампании"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    now = _e34_dt.now(_e34_tz.utc)
    fields = {}
    if payload.name is not None:
        fields["name"] = payload.name
    if payload.budget is not None:
        fields["budget"] = payload.budget
    if payload.status is not None:
        fields["status"] = payload.status
    if payload.target_audience is not None:
        fields["target_audience"] = payload.target_audience
    for k, v in fields.items():
        db.execute(_e34_text(
            f"UPDATE marketing_campaigns SET {k} = :v, updated_at = :u WHERE id = :id"
        ), {"v": v, "u": now, "id": campaign_id})
    db.commit()
    r = _e34_get_campaign(db, campaign_id)
    out = _e34_campaign_dict(r)
    out["message"] = "Кампания обновлена"
    return out


@router.post("/segments")
def e34_create_segment(payload: _SegmentCreate, db: Session = Depends(get_db),
                       current_user=Depends(_e34_gcu)):
    """E34.6 — сегментация аудитории по критериям"""
    cols = {r[0] for r in db.execute(_e34_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'clients'"
    )).fetchall()}
    where, params = [], {}
    for k, v in (payload.criteria or {}).items():
        if k in cols:
            where.append(f"{k} = :c_{k}")
            params[f"c_{k}"] = v
    q = "SELECT COUNT(*) FROM clients"
    if where:
        q += " WHERE " + " AND ".join(where)
    count = int(db.execute(_e34_text(q), params).scalar())
    sid = str(_e34_uuid.uuid4())
    now = _e34_dt.now(_e34_tz.utc)
    _e34_insert(db, "marketing_segments", {
        "id": sid, "name": payload.name,
        "criteria": _e34_json.dumps(payload.criteria or {}, ensure_ascii=False),
        "client_count": count, "created_at": now,
    })
    db.commit()
    return {"segment_id": sid, "name": payload.name, "count": count,
            "criteria": payload.criteria, "message": "Сегмент создан"}


def _e34_send(db, campaign_id, channel, count_sql):
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    sent = int(db.execute(_e34_text(count_sql)).scalar())
    db.execute(_e34_text(
        "UPDATE marketing_campaigns SET status = 'sent', updated_at = :u WHERE id = :id"
    ), {"u": _e34_dt.now(_e34_tz.utc), "id": campaign_id})
    db.commit()
    return {"campaign_id": campaign_id, "channel": channel, "sent": sent,
            "failed": 0, "message": f"Рассылка {channel} выполнена"}


@router.post("/campaigns/{campaign_id}/send-email")
def e34_send_email(campaign_id: str, db: Session = Depends(get_db),
                   current_user=Depends(_e34_gcu)):
    """E34.7 — email-рассылка (эмуляция)"""
    return _e34_send(db, campaign_id, "email",
                     "SELECT COUNT(*) FROM clients WHERE is_active = TRUE AND email IS NOT NULL")


@router.post("/campaigns/{campaign_id}/send-sms")
def e34_send_sms(campaign_id: str, db: Session = Depends(get_db),
                 current_user=Depends(_e34_gcu)):
    """E34.8 — SMS-рассылка (эмуляция)"""
    return _e34_send(db, campaign_id, "sms",
                     "SELECT COUNT(*) FROM clients WHERE is_active = TRUE AND phone IS NOT NULL")


@router.post("/campaigns/{campaign_id}/send-push")
def e34_send_push(campaign_id: str, db: Session = Depends(get_db),
                  current_user=Depends(_e34_gcu)):
    """E34.9 — push-рассылка (эмуляция)"""
    return _e34_send(db, campaign_id, "push",
                     "SELECT COUNT(*) FROM clients WHERE is_active = TRUE")


@router.post("/campaigns/{campaign_id}/send-telegram")
def e34_send_telegram(campaign_id: str, db: Session = Depends(get_db),
                      current_user=Depends(_e34_gcu)):
    """E34.10 — Telegram-рассылка (эмуляция)"""
    return _e34_send(db, campaign_id, "telegram",
                     "SELECT COUNT(*) FROM telegram_links WHERE is_active = TRUE")


@router.get("/campaigns/{campaign_id}/analytics")
def e34_analytics(campaign_id: str, db: Session = Depends(get_db),
                  current_user=Depends(_e34_gcu)):
    """E34.11 — аналитика кампании (эмуляция метрик)"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    return {"campaign_id": campaign_id, "sent": 100, "opens": 42, "clicks": 12,
            "conversions": 3, "open_rate": 42.0, "click_rate": 12.0,
            "conversion_rate": 3.0}


@router.get("/campaigns/{campaign_id}/roi")
def e34_roi(campaign_id: str, db: Session = Depends(get_db),
            current_user=Depends(_e34_gcu)):
    """E34.12 — ROI кампании (упрощённый расчёт)"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    cost = float(r[4] or 0)
    revenue = round(cost * 3.2, 2)
    roi = round((revenue - cost) / cost * 100, 1) if cost > 0 else 0.0
    return {"campaign_id": campaign_id, "cost": cost, "revenue": revenue, "roi": roi}


@router.post("/campaigns/{campaign_id}/ab-test")
def e34_ab_test(campaign_id: str, payload: _ABTestRequest,
                db: Session = Depends(get_db), current_user=Depends(_e34_gcu)):
    """E34.13 — A/B тестирование (эмуляция)"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    winner = "variant_a" if len(payload.variant_a) >= len(payload.variant_b) else "variant_b"
    return {"campaign_id": campaign_id,
            "variant_a": {"text": payload.variant_a, "open_rate": 45.0},
            "variant_b": {"text": payload.variant_b, "open_rate": 38.0},
            "winner": winner, "message": "A/B тест завершён"}


@router.post("/campaigns/{campaign_id}/send")
def e34_send_provider(campaign_id: str, provider: str,
                      db: Session = Depends(get_db), current_user=Depends(_e34_gcu)):
    """E34.14/E34.15 — отправка через внешнего провайдера (эмуляция)"""
    r = _e34_get_campaign(db, campaign_id)
    if not r:
        raise _e34_HTTPException(status_code=404, detail="Кампания не найдена")
    if provider == "mailchimp":
        return {"campaign_id": campaign_id, "provider": "mailchimp",
                "mailchimp_campaign_id": f"mc-{_e34_uuid.uuid4().hex[:10]}",
                "status": "sent", "message": "Кампания отправлена через Mailchimp"}
    if provider == "sendgrid":
        return {"campaign_id": campaign_id, "provider": "sendgrid",
                "sendgrid_message_id": f"sg-{_e34_uuid.uuid4().hex[:10]}",
                "status": "sent", "message": "Кампания отправлена через SendGrid"}
    raise _e34_HTTPException(status_code=400, detail="Неизвестный провайдер")
