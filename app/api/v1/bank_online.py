"""Волна 5: онлайн-эквайринг для пополнения баланса ЛК (без ЮKassa).
Провайдеры: Сбербанк (register.do -> formUrl), Тинькофф (Init -> страница оплаты).
Конфиг — server_settings.BANK_CONFIG (JSON), редактируется в десктопе «Настройки → Сервисы»:
    {"active":"sber",
     "sber":{"mode":"json","merchant_id":"...","token":"..."},
     "tinkoff":{"terminal_key":"...","password":"..."}}
Webhook для кабинета банка: POST /api/v1/bank/webhook
(Сбер: orderNumber+status=DEPOSITED; Тинькофф: JSON Status=CONFIRMED/AUTHORIZED, OrderId).
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text as _t
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.v1.server_settings import get_map
from app.db.session import get_db

router = APIRouter(prefix="/bank", tags=["bank-online"])


def _cfg() -> dict:
    try:
        raw = get_map().get("BANK_CONFIG", "")
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _insert(db: Session, table: str, data: dict):
    cols = {r[0] for r in db.execute(_t(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table}).fetchall()}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    if not data:
        return
    db.execute(_t(f"INSERT INTO {table} ({', '.join(data)}) "
                  f"VALUES ({', '.join(':' + k for k in data)})"), data)


def _tinkoff_token(payload: dict, password: str) -> str:
    vals = [str(v) for k, v in sorted(payload.items())
            if v not in (None, "") and k not in ("Token", "Receipt", "DATA")]
    return hashlib.sha256("".join(vals).encode() + password.encode()).hexdigest()


def create_bank_payment(db: Session, client_id, amount: float, description: str) -> dict | None:
    """Создать платёж у банка-эквайера. None — банк не настроен (вызывающий решает фолбэк)."""
    cfg = _cfg()
    bank = cfg.get("active", "")
    opts = cfg.get(bank) or {}
    oid = f"{bank}_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    url, test_mode = "", True

    if bank == "sber" and opts.get("mode") == "json" and opts.get("merchant_id") and opts.get("token"):
        r = requests.post("https://securepayments.sberbank.ru/payment/rest/register.do", data={
            "userName": opts["merchant_id"], "password": opts["token"],
            "orderNumber": oid, "amount": int(amount * 100), "currency": "643",
            "returnUrl": opts.get("return_url", "https://club.ru/pay/return"),
            "description": description[:120],
        }, timeout=30)
        data = r.json()
        if data.get("errorCode") not in (None, "0"):
            raise HTTPException(502, f"Сбербанк: {data.get('errorMessage', 'ошибка регистрации')}")
        url = data["formUrl"]
        test_mode = False
    elif bank == "tinkoff" and opts.get("terminal_key") and opts.get("password"):
        payload = {"Amount": int(amount * 100), "OrderId": oid,
                   "Description": description[:120], "PayType": "O",
                   "NotificationURL": opts.get("notification_url", "https://club.ru/api/v1/bank/webhook")}
        payload["TerminalKey"] = opts["terminal_key"]
        payload["Token"] = _tinkoff_token(payload, opts["password"])
        r = requests.post("https://securepay.tinkoff.ru/v2/Init", json=payload, timeout=30)
        res = r.json()
        if not res.get("Success"):
            raise HTTPException(502, f"Тинькофф: {res.get('Message', 'ошибка Init')}")
        url = f"https://securepay.tinkoff.ru/v2/{res['PaymentId']}"
        test_mode = False
    else:
        return None  # не настроен

    _insert(db, "payments", {
        "id": str(uuid.uuid4()), "client_id": str(client_id), "amount": amount,
        "currency": "RUB", "payment_method": "bank_card", "status": "pending",
        "external_payment_id": f"bank:{oid}", "payment_system": f"bank:{bank}",
        "notes": description, "payment_direction": "incoming", "payment_category": "service",
        "created_at": now, "updated_at": now})
    db.commit()
    return {"payment_url": url, "order_id": oid, "bank": bank, "test_mode": test_mode}


class BankPaymentIn(BaseModel):
    client_id: str
    amount: float = Field(gt=0)
    description: str = "Пополнение баланса ЛК"


@router.post("/payments", status_code=201)
def create_payment_api(payload: BankPaymentIn, db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    res = create_bank_payment(db, payload.client_id, payload.amount, payload.description)
    if not res:
        raise HTTPException(400, "Банк-эквайринг не настроен (Сервисы → BANK_CONFIG)")
    return res


def _credit_wallet(db: Session, row):
    """Зачисление на кошелёк по строке payments (id, client_id, amount) — как у ЮKassa."""
    now = datetime.now(timezone.utc)
    client_id = str(row[1])
    w = db.execute(_t("SELECT id FROM wallets WHERE CAST(client_id AS TEXT) = :c"),
                   {"c": client_id}).fetchone()
    if w:
        db.execute(_t("UPDATE wallets SET balance = balance + :a WHERE id = :i"),
                   {"a": float(row[2]), "i": str(w[0])})
    else:
        _insert(db, "wallets", {"id": str(uuid.uuid4()), "client_id": client_id,
                                "balance": float(row[2]), "currency": "RUB",
                                "frozen_balance": 0, "created_at": now, "updated_at": now})


@router.post("/webhook")
async def bank_webhook(request: Request, db: Session = Depends(get_db)):
    """Уведомление банка: Сбер (form: orderNumber, status), Тинькофф (JSON: OrderId, Status)."""
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        data = await request.json()
        order_id = data.get("OrderId", "")
        ok = data.get("Status") in ("CONFIRMED", "AUTHORIZED")
    else:
        form = await request.form()
        order_id = form.get("orderNumber", "")
        ok = form.get("status") == "DEPOSITED"
    if not order_id:
        return {"ok": False, "detail": "order не определён"}
    row = db.execute(_t(
        "SELECT id, client_id, amount, status FROM payments "
        "WHERE external_payment_id = :p"), {"p": f"bank:{order_id}"}).first()
    if not row:
        return {"ok": False, "detail": "платёж не найден"}
    if ok and row[3] != "succeeded":
        now = datetime.now(timezone.utc)
        db.execute(_t("UPDATE payments SET status='succeeded', paid_at=:n WHERE id=:i"),
                   {"n": now, "i": str(row[0])})
        _credit_wallet(db, row)
    db.commit()
    return {"ok": True, "order": order_id, "paid": bool(ok)}