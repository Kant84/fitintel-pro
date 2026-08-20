"""E36: Рекуррентные платежи (ТЗ v3.2 §4.7).

Расписания автосписаний по сохранённым картам ЮKassa:
графики (day/week/month), автосписания, ретраи с экспоненциальной
паузой, пауза/возобновление/отмена, история списаний.
"""
import uuid
from datetime import datetime, timedelta
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

router = APIRouter(prefix="/recurring", tags=["recurring"])

_FMT = "%Y-%m-%d %H:%M:%S"
_INTERVALS = ("day", "week", "month")
_FAIL_NEXT = set()  # test-only: schedule_id, чьё следующее списание упадёт


def _now():
    return datetime.now()


def _fmt(dt):
    return dt.strftime(_FMT)


def _advance(dt, unit, count):
    if unit == "day":
        return dt + timedelta(days=count)
    if unit == "week":
        return dt + timedelta(weeks=count)
    return dt + timedelta(days=30 * count)  # month: упрощённо 30 дней


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


def _client_exists(db, client_id):
    try:
        cid = uuid.UUID(str(client_id))
    except (ValueError, AttributeError):
        return False
    row = db.execute(text("SELECT id FROM clients WHERE id=:i"), {"i": cid}).fetchone()
    return row is not None


def _get_schedule(db, schedule_id):
    row = db.execute(
        text("SELECT * FROM recurring_schedules WHERE id=:i"), {"i": schedule_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    return dict(row)


class ScheduleCreate(BaseModel):
    client_id: str
    card_id: Optional[str] = None
    tariff_id: Optional[str] = None
    amount: float
    currency: str = "RUB"
    interval_unit: str = "month"
    interval_count: int = 1
    start_at: Optional[str] = None
    max_retries: int = 3
    description: Optional[str] = None


class ScheduleUpdate(BaseModel):
    amount: Optional[float] = None
    interval_unit: Optional[str] = None
    interval_count: Optional[int] = None
    next_charge_at: Optional[str] = None
    description: Optional[str] = None


class FailNextRequest(BaseModel):
    schedule_id: str


@router.post("/schedules", status_code=201)
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    if payload.interval_unit not in _INTERVALS:
        raise HTTPException(status_code=400, detail="Недопустимый интервал")
    if payload.interval_count < 1:
        raise HTTPException(status_code=400, detail="Количество интервалов должно быть не менее 1")
    if not _client_exists(db, payload.client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    sid = str(uuid.uuid4())
    if payload.start_at:
        next_at = payload.start_at
    else:
        next_at = _fmt(_advance(_now(), payload.interval_unit, payload.interval_count))
    _insert(db, "recurring_schedules", {
        "id": sid,
        "client_id": payload.client_id,
        "card_id": payload.card_id,
        "tariff_id": payload.tariff_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "interval_unit": payload.interval_unit,
        "interval_count": payload.interval_count,
        "next_charge_at": next_at,
        "status": "active",
        "retry_count": 0,
        "max_retries": payload.max_retries,
        "last_error": None,
        "description": payload.description,
        "created_at": _fmt(_now()),
    })
    db.commit()
    return {"schedule_id": sid, "status": "active", "next_charge_at": next_at, "message": "Автоплатёж создан"}


@router.get("/schedules")
def list_schedules(client_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM recurring_schedules WHERE 1=1"
    params = {}
    if client_id:
        q += " AND client_id=:c"
        params["c"] = client_id
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_schedule(db, schedule_id)


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, payload: ScheduleUpdate,
                    db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_schedule(db, schedule_id)
    if payload.amount is not None and payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    if payload.interval_unit is not None and payload.interval_unit not in _INTERVALS:
        raise HTTPException(status_code=400, detail="Недопустимый интервал")
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if fields:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        fields["sid"] = schedule_id
        db.execute(text(f"UPDATE recurring_schedules SET {sets} WHERE id=:sid"), fields)
        db.commit()
    return {"message": "Расписание обновлено"}


@router.post("/schedules/{schedule_id}/pause")
def pause_schedule(schedule_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    sch = _get_schedule(db, schedule_id)
    if sch["status"] != "active":
        raise HTTPException(status_code=400, detail="Автоплатёж не активен")
    db.execute(text("UPDATE recurring_schedules SET status='paused' WHERE id=:i"), {"i": schedule_id})
    db.commit()
    return {"message": "Автоплатёж приостановлен", "status": "paused"}


@router.post("/schedules/{schedule_id}/resume")
def resume_schedule(schedule_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    sch = _get_schedule(db, schedule_id)
    if sch["status"] != "paused":
        raise HTTPException(status_code=400, detail="Автоплатёж не приостановлен")
    next_at = _fmt(_advance(_now(), sch["interval_unit"], sch["interval_count"]))
    db.execute(text("UPDATE recurring_schedules SET status='active', next_charge_at=:n WHERE id=:i"),
               {"n": next_at, "i": schedule_id})
    db.commit()
    return {"message": "Автоплатёж возобновлён", "status": "active", "next_charge_at": next_at}


@router.post("/schedules/{schedule_id}/cancel")
def cancel_schedule(schedule_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    sch = _get_schedule(db, schedule_id)
    if sch["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Автоплатёж уже отменён")
    db.execute(text("UPDATE recurring_schedules SET status='cancelled' WHERE id=:i"), {"i": schedule_id})
    db.commit()
    return {"message": "Автоплатёж отменён", "status": "cancelled"}


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_schedule(db, schedule_id)
    db.execute(text("DELETE FROM recurring_charges WHERE schedule_id=:i"), {"i": schedule_id})
    db.execute(text("DELETE FROM recurring_schedules WHERE id=:i"), {"i": schedule_id})
    db.commit()
    return None


@router.get("/schedules/{schedule_id}/charges")
def list_charges(schedule_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_schedule(db, schedule_id)
    rows = db.execute(
        text("SELECT * FROM recurring_charges WHERE schedule_id=:i ORDER BY created_at DESC"),
        {"i": schedule_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/run")
def run_charges(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    now_s = _fmt(_now())
    rows = db.execute(
        text("SELECT * FROM recurring_schedules WHERE status='active' AND next_charge_at<=:n"),
        {"n": now_s},
    ).mappings().fetchall()
    charged, failed, results = 0, 0, []
    for r in rows:
        sch = dict(r)
        sid = sch["id"]
        attempt = (sch.get("retry_count") or 0) + 1
        if sid in _FAIL_NEXT:
            _FAIL_NEXT.discard(sid)
            err = "Карта отклонена (эмуляция сбоя)"
            if attempt >= (sch.get("max_retries") or 3):
                db.execute(
                    text("UPDATE recurring_schedules SET status='failed', retry_count=:r, last_error='Превышено число попыток списания' WHERE id=:i"),
                    {"r": attempt, "i": sid},
                )
                final = "failed_final"
            else:
                next_at = _fmt(_now() + timedelta(hours=2 ** attempt))
                db.execute(
                    text("UPDATE recurring_schedules SET retry_count=:r, last_error=:e, next_charge_at=:n WHERE id=:i"),
                    {"r": attempt, "e": err, "n": next_at, "i": sid},
                )
                final = "failed_retry"
            _insert(db, "recurring_charges", {
                "id": str(uuid.uuid4()), "schedule_id": sid, "payment_id": None,
                "amount": sch["amount"], "status": "failed", "attempt": attempt,
                "error": err, "created_at": _fmt(_now()),
            })
            failed += 1
            results.append({"schedule_id": sid, "status": final, "attempt": attempt, "error": err})
        else:
            pid = "yk-" + uuid.uuid4().hex[:12]
            next_at = _fmt(_advance(datetime.strptime(sch["next_charge_at"], _FMT),
                                    sch["interval_unit"], sch["interval_count"]))
            db.execute(
                text("UPDATE recurring_schedules SET retry_count=0, last_error=NULL, next_charge_at=:n WHERE id=:i"),
                {"n": next_at, "i": sid},
            )
            _insert(db, "recurring_charges", {
                "id": str(uuid.uuid4()), "schedule_id": sid, "payment_id": pid,
                "amount": sch["amount"], "status": "succeeded", "attempt": attempt,
                "error": None, "created_at": _fmt(_now()),
            })
            charged += 1
            results.append({"schedule_id": sid, "status": "succeeded", "payment_id": pid, "next_charge_at": next_at})
    db.commit()
    return {"charged": charged, "failed": failed, "results": results}


@router.post("/test/fail-next")
def test_fail_next(payload: FailNextRequest, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_schedule(db, payload.schedule_id)
    _FAIL_NEXT.add(payload.schedule_id)
    return {"message": "Следующее списание будет неудачным"}


@router.post("/test/clear")
def test_clear(user=Depends(require_roles("admin"))):
    _FAIL_NEXT.clear()
    return {"message": "Тестовые флаги сброшены"}
