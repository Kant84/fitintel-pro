"""E37: Реферальная программа (ТЗ v3.2 §4.9).

Реф-коды клиентов, атрибуция приглашений, двусторонние бонусы
(реферер + приглашённый), баланс бонусов, выплаты, антифрод
(самоприглашение, повторная регистрация), статистика программы.
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

router = APIRouter(prefix="/referrals", tags=["referrals"])

_FMT = "%Y-%m-%d %H:%M:%S"
DEFAULT_REFERRER_REWARD = 500.0
DEFAULT_REFERRED_REWARD = 300.0


def _fmt(dt):
    return dt.strftime(_FMT)


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


def _get_referral(db, referral_id):
    row = db.execute(
        text("SELECT * FROM referrals WHERE id=:i"), {"i": referral_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Приглашение не найдено")
    return dict(row)


class CodeCreate(BaseModel):
    client_id: str


class RegisterReferral(BaseModel):
    code: str
    referred_client_id: str


class RewardRequest(BaseModel):
    referrer_amount: Optional[float] = None
    referred_amount: Optional[float] = None


class PayoutRequest(BaseModel):
    client_id: str


@router.post("/codes", status_code=201)
def create_code(payload: CodeCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not _client_exists(db, payload.client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    row = db.execute(
        text("SELECT * FROM referral_codes WHERE client_id=:c"), {"c": payload.client_id}
    ).mappings().fetchone()
    if row:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content={"code": row["code"], "client_id": payload.client_id, "existing": True})
    code = "REF-" + uuid.uuid4().hex[:8].upper()
    _insert(db, "referral_codes", {
        "id": str(uuid.uuid4()),
        "client_id": payload.client_id,
        "code": code,
        "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"code": code, "client_id": payload.client_id, "existing": False}


@router.get("/codes/me")
def my_code(client_id: str = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM referral_codes WHERE client_id=:c"), {"c": client_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Реферальный код не найден")
    return dict(row)


@router.get("/codes/{code}")
def validate_code(code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM referral_codes WHERE code=:c"), {"c": code}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Код не найден")
    return {"valid": True, "code": row["code"], "referrer_id": row["client_id"]}


@router.post("/register", status_code=201)
def register_referral(payload: RegisterReferral, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM referral_codes WHERE code=:c"), {"c": payload.code}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Код не найден")
    referrer_id = row["client_id"]
    if referrer_id == payload.referred_client_id:
        raise HTTPException(status_code=400, detail="Нельзя пригласить самого себя")
    dup = db.execute(
        text("SELECT id FROM referrals WHERE referred_id=:r"), {"r": payload.referred_client_id}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Клиент уже зарегистрирован по реферальной программе")
    rid = str(uuid.uuid4())
    _insert(db, "referrals", {
        "id": rid,
        "referrer_id": referrer_id,
        "referred_id": payload.referred_client_id,
        "code": payload.code,
        "status": "registered",
        "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"referral_id": rid, "referrer_id": referrer_id, "status": "registered", "message": "Приглашение зарегистрировано"}


@router.get("")
def list_referrals(referrer_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM referrals WHERE 1=1"
    params = {}
    if referrer_id:
        q += " AND referrer_id=:r"
        params["r"] = referrer_id
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/balance")
def balance(client_id: str = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    accrued = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM referral_rewards WHERE client_id=:c AND status='accrued'"),
        {"c": client_id},
    ).scalar()
    paid = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM referral_rewards WHERE client_id=:c AND status='paid'"),
        {"c": client_id},
    ).scalar()
    return {"client_id": client_id, "accrued": float(accrued or 0), "paid": float(paid or 0),
            "total": float(accrued or 0) + float(paid or 0)}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    total = db.execute(text("SELECT COUNT(*) FROM referrals")).scalar()
    rewarded = db.execute(text("SELECT COUNT(*) FROM referrals WHERE status='rewarded'")).scalar()
    bonuses = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM referral_rewards")
    ).scalar()
    paid = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM referral_rewards WHERE status='paid'")
    ).scalar()
    return {"total_referrals": total, "rewarded": rewarded,
            "bonuses_total": float(bonuses or 0), "bonuses_paid": float(paid or 0)}


@router.post("/payout")
def payout(payload: PayoutRequest, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    rows = db.execute(
        text("SELECT id, amount FROM referral_rewards WHERE client_id=:c AND status='accrued'"),
        {"c": payload.client_id},
    ).mappings().fetchall()
    if not rows:
        raise HTTPException(status_code=400, detail="Нет бонусов к выплате")
    total = sum(float(r["amount"] or 0) for r in rows)
    db.execute(
        text("UPDATE referral_rewards SET status='paid', paid_at=:p WHERE client_id=:c AND status='accrued'"),
        {"p": _fmt(datetime.now()), "c": payload.client_id},
    )
    db.commit()
    return {"client_id": payload.client_id, "paid": total, "count": len(rows), "message": "Бонусы выплачены"}


@router.get("/{referral_id}")
def get_referral(referral_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_referral(db, referral_id)


@router.post("/{referral_id}/reward")
def reward(referral_id: str, payload: RewardRequest, db: Session = Depends(get_db),
           user=Depends(require_roles("admin"))):
    ref = _get_referral(db, referral_id)
    if ref["status"] == "rewarded":
        raise HTTPException(status_code=400, detail="Вознаграждение уже начислено")
    if ref["status"] == "rejected":
        raise HTTPException(status_code=400, detail="Приглашение отклонено")
    ra = payload.referrer_amount if payload.referrer_amount is not None else DEFAULT_REFERRER_REWARD
    rd = payload.referred_amount if payload.referred_amount is not None else DEFAULT_REFERRED_REWARD
    now = _fmt(datetime.now())
    db.execute(
        text("UPDATE referrals SET status='rewarded', referrer_reward=:ra, referred_reward=:rd, rewarded_at=:t WHERE id=:i"),
        {"ra": ra, "rd": rd, "t": now, "i": referral_id},
    )
    _insert(db, "referral_rewards", {
        "id": str(uuid.uuid4()), "referral_id": referral_id, "client_id": ref["referrer_id"],
        "amount": ra, "kind": "referrer_bonus", "status": "accrued", "created_at": now,
    })
    _insert(db, "referral_rewards", {
        "id": str(uuid.uuid4()), "referral_id": referral_id, "client_id": ref["referred_id"],
        "amount": rd, "kind": "referred_bonus", "status": "accrued", "created_at": now,
    })
    db.commit()
    return {"message": "Вознаграждение начислено", "referrer_amount": ra, "referred_amount": rd, "status": "rewarded"}


@router.delete("/{referral_id}", status_code=204)
def delete_referral(referral_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_referral(db, referral_id)
    db.execute(text("DELETE FROM referral_rewards WHERE referral_id=:i"), {"i": referral_id})
    db.execute(text("DELETE FROM referrals WHERE id=:i"), {"i": referral_id})
    db.commit()
    return None
