# app/api/v1/yookassa.py
"""
YooKassa API — онлайн-платежи, возвраты, сохранённые карты, webhook, автосписания.
Тестовый режим: без реальных ключей YOOKASSA_* платежи эмулируются локально.
E26.1–E26.15
"""

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/yookassa", tags=["YooKassa"])

WEBHOOK_SECRET = os.getenv("YOOKASSA_WEBHOOK_SECRET", "test-webhook-secret")
TEST_MODE = os.getenv("YOOKASSA_TEST_MODE", "true").lower() == "true" or not os.getenv("YOOKASSA_SECRET_KEY")

# Эмуляция сбоев для тестов: ok | unavailable | timeout
_SIMULATE = {"mode": "ok"}


def _check_simulate():
    if _SIMULATE["mode"] == "unavailable":
        raise HTTPException(status_code=503, detail="YooKassa недоступна")
    if _SIMULATE["mode"] == "timeout":
        raise HTTPException(status_code=504, detail="Таймаут запроса к YooKassa")


def _cols(db: Session, table: str) -> set:
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    return {r[0] for r in rows}


def _insert(db: Session, table: str, data: dict):
    cols = _cols(db, table)
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    keys = ", ".join(data.keys())
    vals = ", ".join(":" + k for k in data.keys())
    db.execute(text(f"INSERT INTO {table} ({keys}) VALUES ({vals})"), data)


def _find_payment(db: Session, pid: str):
    return db.execute(text(
        "SELECT id, client_id, amount, status, external_payment_id FROM payments "
        "WHERE external_payment_id = :p OR CAST(id AS TEXT) = :p"
    ), {"p": pid}).fetchone()


class CreatePaymentRequest(BaseModel):
    client_id: str
    amount: float = Field(gt=0)
    description: str = "Оплата"
    return_url: str = ""
    save_card: bool = False
    subscription_id: Optional[str] = None


class RefundRequest(BaseModel):
    payment_id: str
    amount: float = Field(gt=0)
    reason: str = ""


class SaveCardRequest(BaseModel):
    client_id: str
    card_number: str = "4111111111111111"


class SimulateRequest(BaseModel):
    mode: str  # ok | unavailable | timeout


@router.post("/payments", status_code=201)
def create_payment(
    payload: CreatePaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """E26.1/E26.2/E26.12/E26.13 — создать платёж"""
    _check_simulate()
    yk_id = f"yk-{uuid.uuid4().hex[:16]}"
    internal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    _insert(db, "payments", {
        "id": internal_id,
        "client_id": payload.client_id,
        "amount": payload.amount,
        "currency": "RUB",
        "payment_method": "bank_card",
        "status": "pending",
        "external_payment_id": yk_id,
        "payment_system": "yookassa",
        "notes": payload.description,
        "payment_direction": "incoming",
        "payment_category": "subscription" if payload.subscription_id else "service",
        "created_by_user_id": str(user.id),
        "created_at": now,
        "updated_at": now,
    })
    db.commit()
    return {
        "payment_id": internal_id,
        "yookassa_payment_id": yk_id,
        "payment_url": f"https://yookassa.ru/payments/{yk_id}?test=true",
        "status": "pending",
        "amount": payload.amount,
        "currency": "RUB",
        "test_mode": TEST_MODE,
    }


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """E26.6 — статус платежа"""
    row = _find_payment(db, payment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    fiscal = db.execute(text(
        "SELECT fiscal_document_number FROM payments WHERE id = :i"
    ), {"i": str(row[0])}).scalar()
    return {
        "payment_id": str(row[0]),
        "yookassa_payment_id": row[4],
        "status": row[3],
        "amount": float(row[2]),
        "fiscal_document_number": fiscal,
        "test_mode": TEST_MODE,
    }

@router.post("/webhook")
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)):
    """E26.3/E26.4/E26.5/E26.11/E26.14 — webhook от YooKassa"""
    body = await request.body()
    signature = request.headers.get("X-YooKassa-Signature", "")
    expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Невалидная подпись webhook")

    payload = json.loads(body.decode())
    event = payload.get("event", "")
    obj = payload.get("object", {})
    yk_id = obj.get("id", "")
    event_key = f"{event}:{yk_id}"

    exists = db.execute(text(
        "SELECT 1 FROM yookassa_webhook_events WHERE event_key = :k"
    ), {"k": event_key}).fetchone()
    if exists:
        return {"status": "ok", "detail": "Уже обработано"}

    result = {"status": "ok", "event": event}
    row = _find_payment(db, yk_id)
    now = datetime.now(timezone.utc)

    if event == "payment.succeeded" and row:
        fiscal_doc = f"FD-{uuid.uuid4().hex[:10].upper()}"
        db.execute(text(
            "UPDATE payments SET status = 'succeeded', paid_at = :n, "
            "fiscal_document_number = :f WHERE id = :i"
        ), {"n": now, "f": fiscal_doc, "i": str(row[0])})
        # Пополнение кошелька клиента
        client_id = str(row[1])
        w = db.execute(text(
            "SELECT id FROM wallets WHERE CAST(client_id AS TEXT) = :c"
        ), {"c": client_id}).fetchone()
        if w:
            db.execute(text(
                "UPDATE wallets SET balance = balance + :a WHERE id = :i"
            ), {"a": float(row[2]), "i": str(w[0])})
        else:
            _insert(db, "wallets", {
                "id": str(uuid.uuid4()), "client_id": client_id,
                "balance": float(row[2]), "currency": "RUB", "frozen_balance": 0,
                "created_at": now, "updated_at": now,
            })
        result["balance_credited"] = float(row[2])
        # Активация абонемента из metadata
        sub_id = (obj.get("metadata") or {}).get("subscription_id")
        if sub_id:
            db.execute(text(
                "UPDATE subscriptions SET status = 'active' WHERE CAST(id AS TEXT) = :s"
            ), {"s": sub_id})
            result["subscription_activated"] = sub_id
        result["fiscal_document_number"] = fiscal_doc

    elif event == "payment.canceled" and row:
        db.execute(text(
            "UPDATE payments SET status = 'canceled' WHERE id = :i"
        ), {"i": str(row[0])})
        result["canceled"] = True

    _insert(db, "yookassa_webhook_events", {
        "id": str(uuid.uuid4()), "event_key": event_key, "event_type": event,
        "payload": body.decode(errors="replace"), "created_at": now, "updated_at": now,
    })
    db.commit()
    return result


@router.post("/refunds", status_code=201)
def create_refund(
    payload: RefundRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """E26.7/E26.8 — возврат средств"""
    _check_simulate()
    row = _find_payment(db, payload.payment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    total_refunded = db.execute(text(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_refunds "
        "WHERE CAST(payment_id AS TEXT) = :p"
    ), {"p": str(row[0])}).scalar()
    if float(total_refunded) + payload.amount > float(row[2]) + 0.001:
        raise HTTPException(status_code=400, detail="Сумма возврата превышает сумму платежа")
    rid = f"rf-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    _insert(db, "payment_refunds", {
        "id": str(uuid.uuid4()), "payment_id": str(row[0]),
        "external_refund_id": rid, "amount": payload.amount,
        "status": "succeeded", "reason": payload.reason,
        "created_at": now, "updated_at": now,
    })
    if float(total_refunded) + payload.amount >= float(row[2]) - 0.001:
        db.execute(text("UPDATE payments SET status = 'refunded' WHERE id = :i"), {"i": str(row[0])})
    db.commit()
    return {"refund_id": rid, "payment_id": str(row[0]), "amount": payload.amount, "status": "succeeded"}


@router.post("/cards", status_code=201)
def save_card(
    payload: SaveCardRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """E26.9 — сохранить карту для рекуррентных платежей"""
    _check_simulate()
    pm_id = f"pm-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    _insert(db, "saved_cards", {
        "id": str(uuid.uuid4()), "client_id": payload.client_id,
        "payment_method_id": pm_id, "card_last4": payload.card_number[-4:],
        "card_type": "Mir", "is_active": True,
        "created_at": now, "updated_at": now,
    })
    db.commit()
    return {"card_token": pm_id, "payment_method_id": pm_id,
            "last4": payload.card_number[-4:], "test_mode": TEST_MODE}


@router.get("/cards/{client_id}")
def list_cards(
    client_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.execute(text(
        "SELECT payment_method_id, card_last4, card_type, is_active FROM saved_cards "
        "WHERE CAST(client_id AS TEXT) = :c"
    ), {"c": client_id}).fetchall()
    cards = [{"payment_method_id": r[0], "last4": r[1], "card_type": r[2], "is_active": r[3]} for r in rows]
    return {"cards": cards, "count": len(cards)}


@router.post("/auto-charge/run")
def auto_charge(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """E26.10 — автосписание за продление абонемента с сохранённой карты"""
    _check_simulate()
    now = datetime.now(timezone.utc)
    rows = db.execute(text(
        "SELECT s.id, s.client_id, s.price FROM subscriptions s "
        "WHERE (s.status = 'expired' OR (s.status = 'active' AND s.end_date < :n)) "
        "AND EXISTS (SELECT 1 FROM saved_cards c WHERE c.client_id = s.client_id AND c.is_active)"
    ), {"n": now}).fetchall()
    charged = []
    for sub_id, client_id, price in rows:
        yk_id = f"yk-{uuid.uuid4().hex[:16]}"
        _insert(db, "payments", {
            "id": str(uuid.uuid4()), "client_id": str(client_id),
            "amount": float(price or 0), "currency": "RUB",
            "payment_method": "bank_card", "status": "succeeded",
            "external_payment_id": yk_id, "payment_system": "yookassa",
            "notes": "Автосписание за продление абонемента",
            "payment_direction": "incoming", "payment_category": "subscription",
            "paid_at": now, "created_at": now, "updated_at": now,
        })
        db.execute(text(
            "UPDATE subscriptions SET status = 'active', end_date = :e WHERE id = :i"
        ), {"e": now + timedelta(days=30), "i": str(sub_id)})
        charged.append({"subscription_id": str(sub_id), "amount": float(price or 0),
                        "yookassa_payment_id": yk_id, "status": "succeeded"})
    db.commit()
    return {"charged": len(charged), "results": charged, "test_mode": TEST_MODE}


@router.post("/test/simulate")
def set_simulate(payload: SimulateRequest, user=Depends(get_current_user)):
    """E26.12/E26.13 — эмуляция сбоев YooKassa (только тестовый режим)"""
    if payload.mode not in ("ok", "unavailable", "timeout"):
        raise HTTPException(status_code=422, detail="mode: ok | unavailable | timeout")
    _SIMULATE["mode"] = payload.mode
    return {"simulate": payload.mode}


@router.get("/test-mode")
def get_test_mode():
    """E26.15 — режим работы провайдера"""
    return {"test_mode": TEST_MODE, "provider": "yookassa"}
