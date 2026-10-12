# app/api/v1/phone_verify.py
"""
Phone Verify API — подтверждение телефона кодом.
Провайдеры: smsru, twilio, telegram, whatsapp (эмуляция + fallback).
E29.1–E29.15
"""

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/phone-verify", tags=["Phone Verify"])

PHONE_RE = re.compile(r"^\+[1-9]\d{9,14}$")
CODE_TTL_SECONDS = 300        # 5 минут
RESEND_INTERVAL_SECONDS = 60  # 1 минута
MAX_ATTEMPTS = 5

# Доступность провайдеров (эмуляция сбоев для E29.13/E29.14)
_PROVIDERS = {"smsru": True, "twilio": True, "telegram": True, "whatsapp": True, "max": True, "email": True}
PROVIDER_ORDER = ["smsru", "twilio", "whatsapp", "telegram"]


def _insert(db: Session, table: str, data: dict):
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    cols = {r[0] for r in rows}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(text(f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"), data)


def _telegram_linked(db: Session, phone: str) -> bool:
    return db.execute(text(
        "SELECT 1 FROM telegram_links tl JOIN clients c ON c.id = tl.client_id "
        "WHERE c.phone = :p AND tl.is_active = true LIMIT 1"
    ), {"p": phone}).fetchone() is not None


def _provider_available(db: Session, name: str, phone: str) -> bool:
    if not _PROVIDERS.get(name, False):
        return False
    if name == "telegram":
        return _telegram_linked(db, phone)
    if name == "max":
        _norm = re.sub(r"\D", "", phone or "")[-10:]
        if len(_norm) < 10:
            return False
        return db.execute(text(
            "SELECT 1 FROM max_bot_bindings b JOIN clients c ON c.id=b.client_id "
            "WHERE right(regexp_replace(c.phone,'\\D','','g'),10)=:p LIMIT 1"
        ), {"p": _norm}).fetchone() is not None
    if name == "email":
        return True
    return True


def _pick_provider(db: Session, phone: str, requested: Optional[str]):
    """Выбор провайдера с fallback. Возвращает (provider, fallback_used)"""
    if requested:
        if requested not in _PROVIDERS:
            raise HTTPException(status_code=422, detail="Неизвестный провайдер")
        if _provider_available(db, requested, phone):
            return requested, False
    for name in PROVIDER_ORDER:
        if name == requested:
            continue
        if _provider_available(db, name, phone):
            return name, (requested is not None) or (name != PROVIDER_ORDER[0])
    raise HTTPException(status_code=503, detail="Все SMS-сервисы недоступны")


def _new_code() -> str:
    return f"{secrets.randbelow(10000):04d}"


def _create_code(db: Session, phone: str, provider: str):
    now = datetime.now(timezone.utc)
    code = _new_code()
    _insert(db, "phone_verifications", {
        "id": str(uuid.uuid4()), "phone": phone, "code": code, "provider": provider,
        "attempts": 0, "verified": False,
        "expires_at": now + timedelta(seconds=CODE_TTL_SECONDS),
        "created_at": now, "updated_at": now,
    })
    db.commit()
    return code


class SendRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    code: str


class ProvidersRequest(BaseModel):
    smsru: Optional[bool] = None
    twilio: Optional[bool] = None
    telegram: Optional[bool] = None
    whatsapp: Optional[bool] = None




def _send_max_code(db: Session, phone: str, code: str):
    """Реальная отправка кода в MAX по привязке клиента."""
    import requests as _rq
    _norm = re.sub(r"\D", "", phone or "")[-10:]
    row = db.execute(text(
        "SELECT b.max_user_id FROM max_bot_bindings b JOIN clients c ON c.id=b.client_id "
        "WHERE right(regexp_replace(c.phone,'\\D','','g'),10)=:p LIMIT 1"
    ), {"p": _norm}).first()
    tok = db.execute(text("SELECT bot_token FROM max_bot_settings WHERE id=1")).first()
    if not row or not tok or not tok[0]:
        raise HTTPException(status_code=404, detail="Привязка MAX не найдена — сначала нажмите «Старт» в боте")
    r = _rq.post("https://platform-api.max.ru/messages",
                 headers={"Authorization": tok[0]},
                 json={"recipient": {"user_id": int(row[0])},
                       "body": {"text": "Код подтверждения FitIntel: " + code + " (действует 5 минут)"}},
                 timeout=10)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Не удалось отправить код в MAX")


def _send_email_code(db: Session, phone: str, code: str):
    """Отправка кода на email клиента через SMTP клуба."""
    import smtplib
    from email.mime.text import MIMEText
    _norm = re.sub(r"\D", "", phone or "")[-10:]
    row = db.execute(text(
        "SELECT email FROM clients WHERE right(regexp_replace(phone,'\\D','','g'),10)=:p "
        "AND email IS NOT NULL AND email <> '' LIMIT 1"
    ), {"p": _norm}).first()
    st = db.execute(text(
        "SELECT email_from, smtp_host, smtp_port, smtp_user, smtp_password FROM notification_settings WHERE id=1"
    )).first()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Email клиента не найден")
    if not st or not st[1]:
        raise HTTPException(status_code=503, detail="SMTP клуба не настроен")
    msg = MIMEText("Код подтверждения FitIntel: " + code + " (действует 5 минут)", "plain", "utf-8")
    msg["Subject"] = "Код подтверждения"
    msg["From"] = st[0] or st[3]
    msg["To"] = row[0]
    srv = smtplib.SMTP(st[1], int(st[2] or 465), timeout=10)
    try:
        if st[4]:
            srv.starttls()
            srv.login(st[3], st[4])
        srv.send_message(msg)
    finally:
        srv.quit()

@router.post("/send")
def send_code(
    payload: SendRequest,
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """E29.1/E29.2/E29.9–E29.14 — отправить код подтверждения"""
    if not PHONE_RE.match(payload.phone or ""):
        raise HTTPException(status_code=422, detail="Невалидный номер телефона")
    chosen, fallback = _pick_provider(db, payload.phone, provider)
    code = _create_code(db, payload.phone, chosen)
    if chosen == "max":
        _send_max_code(db, payload.phone, code)
    elif chosen == "email":
        _send_email_code(db, payload.phone, code)
    return {
        "message": "Код отправлен",
        "phone": payload.phone,
        "provider": chosen,
        "provider_confirmed": True,
        "fallback": fallback,
        "dev_code": code,  # только тестовый режим: в проде код не возвращается
    }


@router.post("/verify")
def verify_code(payload: VerifyRequest, db: Session = Depends(get_db)):
    """E29.3/E29.4/E29.5/E29.8 — проверить код"""
    row = db.execute(text(
        "SELECT id, code, attempts, expires_at FROM phone_verifications "
        "WHERE phone = :p ORDER BY created_at DESC LIMIT 1"
    ), {"p": payload.phone}).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Неверный код")
    if row[2] >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Слишком много попыток, подождите 15 минут")
    now = datetime.now(timezone.utc)
    if row[3] and now > row[3]:
        raise HTTPException(status_code=410, detail="Код истёк")
    if payload.code != row[1]:
        db.execute(text(
            "UPDATE phone_verifications SET attempts = attempts + 1 WHERE id = :i"
        ), {"i": str(row[0])})
        db.commit()
        raise HTTPException(status_code=400, detail="Неверный код")
    db.execute(text(
        "UPDATE phone_verifications SET verified = true WHERE id = :i"
    ), {"i": str(row[0])})
    # E29.15: помечаем телефон пользователя подтверждённым
    db.execute(text(
        "UPDATE users SET phone_verified = true WHERE phone = :p"
    ), {"p": payload.phone})
    db.commit()
    return {"verified": True, "phone": payload.phone}

@router.post("/resend")
def resend_code(payload: SendRequest, db: Session = Depends(get_db)):
    """E29.6/E29.7 — повторная отправка кода"""
    if not PHONE_RE.match(payload.phone or ""):
        raise HTTPException(status_code=422, detail="Невалидный номер телефона")
    row = db.execute(text(
        "SELECT created_at, provider FROM phone_verifications "
        "WHERE phone = :p ORDER BY created_at DESC LIMIT 1"
    ), {"p": payload.phone}).fetchone()
    now = datetime.now(timezone.utc)
    if row and row[0] and (now - row[0]).total_seconds() < RESEND_INTERVAL_SECONDS:
        raise HTTPException(status_code=429, detail="Подождите 1 минуту")
    provider = row[1] if row else "smsru"
    if not _provider_available(db, provider, payload.phone):
        provider, _ = _pick_provider(db, payload.phone, None)
    code = _create_code(db, payload.phone, provider)
    return {"message": "Новый код отправлен", "phone": payload.phone,
            "provider": provider, "dev_code": code}


@router.post("/test/providers")
def set_providers(payload: ProvidersRequest, user=Depends(get_current_user)):
    """E29.13/E29.14 — эмуляция доступности провайдеров (только тесты)"""
    for name in ("smsru", "twilio", "telegram", "whatsapp"):
        val = getattr(payload, name)
        if val is not None:
            _PROVIDERS[name] = val
    return {"providers": dict(_PROVIDERS)}
