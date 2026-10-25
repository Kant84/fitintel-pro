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
import hmac
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
    """Token Т-Банка: Password участвует в общей сортировке полей."""
    values = {
        key: value
        for key, value in payload.items()
        if value not in (None, "") and key not in ("Token", "Receipt", "DATA")
    }
    values["Password"] = password
    raw = "".join(str(values[key]) for key in sorted(values))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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


def _sber_checksum(payload: dict, callback_token: str) -> str:
    """Контрольная сумма callback Сбера с симметричным ключом."""
    values = {
        key: value
        for key, value in payload.items()
        if key not in ("checksum", "sign_alias")
    }
    raw = "".join(
        f"{key};{values[key]};"
        for key in sorted(values)
    )
    return hmac.new(
        callback_token.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _bank_config(provider: str) -> dict:
    config = _cfg().get(provider) or {}
    if not isinstance(config, dict):
        return {}
    return config


def _verify_tbank_notification(payload: dict) -> None:
    config = _bank_config("tinkoff")
    password = config.get("password", "")
    if not password:
        raise HTTPException(
            status_code=503,
            detail="Т-Банк: password для webhook не настроен",
        )

    received = str(payload.get("Token") or "")
    if not received:
        raise HTTPException(
            status_code=401,
            detail="Т-Банк: обязательный Token отсутствует",
        )

    terminal_key = config.get("terminal_key", "")
    if terminal_key and payload.get("TerminalKey") != terminal_key:
        raise HTTPException(
            status_code=401,
            detail="Т-Банк: неверный TerminalKey",
        )

    expected = _tinkoff_token(payload, password)
    if not hmac.compare_digest(received.lower(), expected.lower()):
        raise HTTPException(
            status_code=401,
            detail="Т-Банк: неверный Token",
        )


def _verify_sber_notification(payload: dict) -> None:
    config = _bank_config("sber")
    callback_token = config.get("callback_token", "")
    if not callback_token:
        raise HTTPException(
            status_code=503,
            detail="Сбер: callback_token для webhook не настроен",
        )

    received = str(payload.get("checksum") or "")
    if not received:
        raise HTTPException(
            status_code=401,
            detail="Сбер: обязательный checksum отсутствует",
        )

    expected = _sber_checksum(payload, callback_token)
    if not hmac.compare_digest(received.lower(), expected.lower()):
        raise HTTPException(
            status_code=401,
            detail="Сбер: неверный checksum",
        )


def _ensure_bank_webhook_events(db: Session) -> None:
    """Общий с generic webhook журнал, без сохранения платёжного payload."""
    db.execute(_t(
        "CREATE TABLE IF NOT EXISTS payment_webhook_events ("
        "id VARCHAR(36) PRIMARY KEY, "
        "event_key VARCHAR(512) NOT NULL UNIQUE, "
        "payment_system VARCHAR(50) NOT NULL, "
        "external_payment_id VARCHAR(255), "
        "event_status VARCHAR(50), "
        "payload_hash VARCHAR(64) NOT NULL, "
        "created_at TIMESTAMP NOT NULL)"
    ))
    db.commit()


def _debit_wallet(db: Session, row) -> None:
    """Снять полный возврат с кошелька, не допуская отрицательный баланс."""
    client_id = str(row[1])
    amount = float(row[2])
    wallet = db.execute(_t(
        "SELECT id, balance FROM wallets WHERE CAST(client_id AS TEXT) = :c"
    ), {"c": client_id}).fetchone()
    if not wallet or float(wallet[1]) + 0.00001 < amount:
        raise HTTPException(
            status_code=409,
            detail="Недостаточно средств кошелька для подтверждения возврата",
        )
    db.execute(_t(
        "UPDATE wallets SET balance = balance - :a WHERE id = :i"
    ), {"a": amount, "i": str(wallet[0])})


def _validate_bank_amount(data: dict, provider: str, row) -> None:
    """Если банк передал сумму, сверить её в минорных единицах."""
    raw_amount = data.get("Amount") if provider == "tinkoff" else data.get("amount")
    if raw_amount in (None, ""):
        return
    try:
        received = int(raw_amount)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Неверная сумма webhook") from exc
    expected = int(round(float(row[2]) * 100))
    if received != expected:
        raise HTTPException(
            status_code=400,
            detail="Сумма webhook не совпадает с платежом",
        )


@router.post("/webhook")
@router.get("/webhook")
async def bank_webhook(request: Request, db: Session = Depends(get_db)):
    """Подписанные уведомления Т-Банка и Сбера с persisted-антидублем."""
    raw_body = await request.body()

    if request.method == "GET":
        provider = "sber"
        data = dict(request.query_params)
        signed_bytes = request.url.query.encode("utf-8")
    elif "application/json" in request.headers.get("content-type", ""):
        provider = "tinkoff"
        signed_bytes = raw_body
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Неверный JSON webhook") from exc
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Webhook JSON должен быть объектом")
    else:
        provider = "sber"
        signed_bytes = raw_body
        data = dict(await request.form())

    if provider == "tinkoff":
        _verify_tbank_notification(data)
        order_id = str(data.get("OrderId") or "")
        bank_status = str(data.get("Status") or "").upper()
        succeeded = bank_status == "CONFIRMED"
        canceled = bank_status in ("CANCELED", "REJECTED", "EXPIRED")
        refunded = bank_status == "REFUNDED"
        event_id = str(data.get("PaymentId") or order_id)
    else:
        _verify_sber_notification(data)
        order_id = str(data.get("orderNumber") or "")
        operation = str(data.get("operation") or "").lower()
        operation_status = str(data.get("status") or "").lower()
        succeeded = (
            operation == "deposited" and operation_status in ("", "1")
        ) or operation_status == "deposited"
        canceled = operation in ("reversed", "declinedbytimeout")
        refunded = operation == "refunded" and operation_status in ("", "1")
        event_id = str(data.get("mdOrder") or order_id)

    if not order_id:
        raise HTTPException(status_code=400, detail="order не определён")
    if not (succeeded or canceled or refunded):
        raise HTTPException(status_code=400, detail="Неподдерживаемый статус webhook")

    payload_hash = hashlib.sha256(signed_bytes).hexdigest()
    event_name = "succeeded" if succeeded else "refunded" if refunded else "canceled"
    event_key = f"bank:{provider}:{order_id}:{event_id}:{event_name}"

    _ensure_bank_webhook_events(db)
    duplicate = db.execute(_t(
        "SELECT 1 FROM payment_webhook_events WHERE event_key = :k"
    ), {"k": event_key}).fetchone()
    if duplicate:
        return {"ok": True, "duplicate": True, "order": order_id}

    row = db.execute(_t(
        "SELECT id, client_id, amount, status FROM payments "
        "WHERE external_payment_id = :p"
    ), {"p": f"bank:{order_id}"}).first()
    if not row:
        raise HTTPException(status_code=404, detail="платёж не найден")

    _validate_bank_amount(data, provider, row)
    current_status = str(row[3]).lower()
    already_applied = False
    now = datetime.now(timezone.utc)

    if succeeded:
        if current_status == "succeeded":
            already_applied = True
        elif current_status != "pending":
            raise HTTPException(status_code=409, detail="Недопустимый переход статуса")
        else:
            db.execute(_t(
                "UPDATE payments SET status='succeeded', paid_at=:n WHERE id=:i"
            ), {"n": now, "i": str(row[0])})
            _credit_wallet(db, row)
    elif canceled:
        if current_status == "canceled":
            already_applied = True
        elif current_status != "pending":
            raise HTTPException(status_code=409, detail="Недопустимый переход статуса")
        else:
            db.execute(_t(
                "UPDATE payments SET status='canceled' WHERE id=:i"
            ), {"i": str(row[0])})
    else:
        if current_status == "refunded":
            already_applied = True
        elif current_status != "succeeded":
            raise HTTPException(status_code=409, detail="Недопустимый переход статуса")
        else:
            _debit_wallet(db, row)
            db.execute(_t(
                "UPDATE payments SET status='refunded' WHERE id=:i"
            ), {"i": str(row[0])})

    db.execute(_t(
        "INSERT INTO payment_webhook_events "
        "(id, event_key, payment_system, external_payment_id, "
        "event_status, payload_hash, created_at) "
        "VALUES (:id, :event_key, :payment_system, "
        ":external_payment_id, :event_status, :payload_hash, :created_at)"
    ), {
        "id": str(uuid.uuid4()),
        "event_key": event_key,
        "payment_system": f"bank:{provider}",
        "external_payment_id": f"bank:{order_id}",
        "event_status": event_name,
        "payload_hash": payload_hash,
        "created_at": now,
    })
    db.commit()
    return {
        "ok": True,
        "duplicate": already_applied,
        "order": order_id,
        "paid": succeeded,
        "canceled": canceled,
        "refunded": refunded,
    }
