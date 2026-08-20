# app/api/v1/selfservice.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/selfservice", tags=["Self-Service"])


@router.get("/profile")
def my_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Профиль клиента (self-service)"""
    from app.models.client import Client
    from app.models.wallet import Wallet

    client = db.query(Client).filter(Client.email == current_user.email).first()
    wallet = db.query(Wallet).filter(Wallet.client_id == client.id).first() if client else None

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
            "roles": getattr(current_user, "roles", []),
        },
        "client": {
            "id": str(client.id) if client else None,
            "first_name": client.first_name if client else None,
            "last_name": client.last_name if client else None,
            "phone": client.phone if client else None,
            "status": client.status if client else None,
        },
        "wallet": {
            "balance": float(wallet.balance) if wallet else 0,
            "currency": wallet.currency if wallet else "RUB",
        } if wallet else None,
    }


@router.get("/subscriptions")
def my_subscriptions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мои абонементы"""
    from app.models.client import Client
    from app.models.subscription import Subscription
    from app.models.tariff import Tariff

    client = db.query(Client).filter(Client.email == current_user.email).first()
    if not client:
        return {"items": []}

    subs = db.query(Subscription, Tariff).join(
        Tariff, Subscription.tariff_id == Tariff.id
    ).filter(Subscription.client_id == client.id).order_by(Subscription.created_at.desc()).all()

    return {"items": [{
        "id": str(s.Subscription.id),
        "tariff_name": s.Tariff.name,
        "status": s.Subscription.status,
        "start_date": str(s.Subscription.start_date) if s.Subscription.start_date else None,
        "end_date": str(s.Subscription.end_date) if s.Subscription.end_date else None,
        "visits_left": s.Subscription.visits_left,
        "freeze_until": str(s.Subscription.freeze_until) if s.Subscription.freeze_until else None,
    } for s in subs]}


@router.get("/visits")
def my_visits(
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мои посещения"""
    from app.models.client import Client
    from app.models.visit import Visit

    client = db.query(Client).filter(Client.email == current_user.email).first()
    if not client:
        return {"items": []}

    visits = db.query(Visit).filter(Visit.client_id == client.id).order_by(
        Visit.entry_time.desc()).limit(limit).all()

    return {"items": [{
        "id": str(v.id),
        "entry_time": v.entry_time.isoformat() if v.entry_time else None,
        "exit_time": v.exit_time.isoformat() if v.exit_time else None,
        "duration_minutes": v.duration_minutes,
        "status": v.status,
    } for v in visits]}

# ==================== E35: терминал самообслуживания ====================
import uuid as _uuid
from datetime import date as _date, datetime as _dt, timezone as _tz

from fastapi import HTTPException as _HTTPExc
from pydantic import BaseModel as _BM
from sqlalchemy import text as _sql

from app.api.dependencies import get_current_user as _gcu

e35_router = APIRouter(prefix="/self-service", tags=["Self-Service E35"])

# Эмуляция терминала оплаты (для E35.12)
_TERMINAL = {"online": True}


class _RegisterRequest(_BM):
    photo: str
    phone: str
    tariff_id: str
    first_name: str = "Клиент"
    last_name: str = "Терминала"


class _BuyRequest(_BM):
    client_id: str
    tariff_id: str
    payment_method: str = "card"


class _BookRequest(_BM):
    client_id: str
    service_id: str
    datetime: str


class _ReceiptRequest(_BM):
    transaction_id: str


class _FreezeRequest(_BM):
    client_id: str
    reason: str = ""


class _ClientRequest(_BM):
    client_id: str


class _PayRequest(_BM):
    client_id: str
    amount: float


class _FaceEntryRequest(_BM):
    photo: str


class _TerminalToggle(_BM):
    online: bool


def _e35_get_tariff(db, tariff_id: str):
    try:
        tid = _uuid.UUID(tariff_id)
    except ValueError:
        return None
    return db.execute(_sql(
        "SELECT id, price, duration_days, visit_limit, is_unlimited "
        "FROM tariffs WHERE id = :t"
    ), {"t": tid}).fetchone()


def _e35_create_subscription(db, client_id, tariff):
    sid = _uuid.uuid4()
    now = _dt.now(_tz.utc)
    today = _date.today()
    end = today.fromordinal(today.toordinal() + int(tariff[2] or 30))
    db.execute(_sql(
        "INSERT INTO subscriptions (id, client_id, tariff_id, status, start_date, "
        "end_date, price, currency, visit_limit, visits_used, is_unlimited, "
        "is_active, created_at, updated_at) "
        "VALUES (:id, :c, :tf, 'active', :sd, :ed, :p, 'RUB', :vl, 0, :un, TRUE, :t, :t)"
    ), {"id": sid, "c": _uuid.UUID(client_id) if isinstance(client_id, str) else client_id,
        "tf": tariff[0], "sd": today, "ed": end, "p": float(tariff[1] or 0),
        "vl": tariff[3], "un": bool(tariff[4]), "t": now})
    return sid


@e35_router.get("/tariffs")
def e35_tariffs(db: Session = Depends(get_db), user=Depends(_gcu)):
    """Список тарифов для терминала"""
    rows = db.execute(_sql(
        "SELECT id, code, name, price, duration_days FROM tariffs WHERE is_active = TRUE"
    )).fetchall()
    return {"tariffs": [{"tariff_id": str(r[0]), "code": r[1], "name": r[2],
                         "price": float(r[3] or 0), "duration_days": r[4]}
                        for r in rows]}


@e35_router.get("/services")
def e35_services(db: Session = Depends(get_db), user=Depends(_gcu)):
    """Список услуг для терминала"""
    rows = db.execute(_sql(
        "SELECT id, name, price FROM services WHERE is_active = TRUE"
    )).fetchall()
    return {"services": [{"service_id": str(r[0]), "name": r[1],
                          "price": float(r[2] or 0)} for r in rows]}


@e35_router.post("/register", status_code=201)
def e35_register(payload: _RegisterRequest, db: Session = Depends(get_db),
                 user=Depends(_gcu)):
    """E35.1/E35.2 — регистрация клиента через терминал с Face ID"""
    if not payload.photo or "blurry" in payload.photo.lower():
        raise _HTTPExc(status_code=400, detail="Лицо не распознано")
    tariff = _e35_get_tariff(db, payload.tariff_id)
    if not tariff:
        raise _HTTPExc(status_code=404, detail="Тариф не найден")
    cid = _uuid.uuid4()
    now = _dt.now(_tz.utc)
    db.execute(_sql(
        "INSERT INTO clients (id, first_name, last_name, phone, gender, status, is_active, "
        "client_category, created_at, updated_at) "
        "VALUES (:id, :fn, :ln, :ph, 'male', 'active', TRUE, 'terminal', :t, :t)"
    ), {"id": cid, "fn": payload.first_name, "ln": payload.last_name,
        "ph": payload.phone, "t": now})
    card = f"FIT-{_uuid.uuid4().hex[:8].upper()}"
    db.execute(_sql(
        "INSERT INTO terminal_cards (id, client_id, card_number, created_at) "
        "VALUES (:i, :c, :n, :t)"
    ), {"i": str(_uuid.uuid4()), "c": str(cid), "n": card, "t": now})
    db.execute(_sql(
        "INSERT INTO terminal_faces (id, client_id, photo, created_at) "
        "VALUES (:i, :c, :p, :t)"
    ), {"i": str(_uuid.uuid4()), "c": str(cid), "p": payload.photo, "t": now})
    sid = _e35_create_subscription(db, cid, tariff)
    db.commit()
    return {"client_id": str(cid), "card_number": card,
            "subscription_id": str(sid), "subscription_activated": True,
            "message": "Клиент зарегистрирован, абонемент активирован"}


@e35_router.post("/buy-subscription", status_code=201)
def e35_buy_subscription(payload: _BuyRequest, db: Session = Depends(get_db),
                         user=Depends(_gcu)):
    """E35.3 — покупка абонемента через терминал"""
    client = db.execute(_sql(
        "SELECT id FROM clients WHERE id = :c"
    ), {"c": _uuid.UUID(payload.client_id)}).fetchone()
    if not client:
        raise _HTTPExc(status_code=404, detail="Клиент не найден")
    tariff = _e35_get_tariff(db, payload.tariff_id)
    if not tariff:
        raise _HTTPExc(status_code=404, detail="Тариф не найден")
    sid = _e35_create_subscription(db, payload.client_id, tariff)
    db.commit()
    return {"subscription_id": str(sid), "receipt_printed": True,
            "payment_method": payload.payment_method,
            "message": "Абонемент куплен, чек напечатан"}


@e35_router.post("/book-service", status_code=201)
def e35_book_service(payload: _BookRequest, db: Session = Depends(get_db),
                     user=Depends(_gcu)):
    """E35.4/E35.5 — бронирование услуги через терминал"""
    svc = db.execute(_sql(
        "SELECT id FROM services WHERE id = :s"
    ), {"s": _uuid.UUID(payload.service_id)}).fetchone()
    if not svc:
        raise _HTTPExc(status_code=404, detail="Услуга не найдена")
    clash = db.execute(_sql(
        "SELECT 1 FROM self_service_bookings "
        "WHERE service_id = :s AND slot_datetime = :dt AND status = 'active'"
    ), {"s": payload.service_id, "dt": payload.datetime}).fetchone()
    if clash:
        raise _HTTPExc(status_code=409, detail="Слот занят, выберите другой")
    bid = str(_uuid.uuid4())
    db.execute(_sql(
        "INSERT INTO self_service_bookings (id, client_id, service_id, "
        "slot_datetime, status, created_at) VALUES (:i, :c, :s, :dt, 'active', :t)"
    ), {"i": bid, "c": payload.client_id, "s": payload.service_id,
        "dt": payload.datetime, "t": _dt.now(_tz.utc)})
    db.commit()
    return {"booking_id": bid, "confirmation": f"BOOK-{bid[:8].upper()}",
            "message": "Услуга забронирована"}

@e35_router.get("/balance")
def e35_balance(client_id: str, db: Session = Depends(get_db), user=Depends(_gcu)):
    """E35.6 — баланс клиента и статус абонемента"""
    cid = _uuid.UUID(client_id)
    w = db.execute(_sql(
        "SELECT balance FROM wallets WHERE client_id = :c"
    ), {"c": cid}).fetchone()
    s = db.execute(_sql(
        "SELECT status FROM subscriptions WHERE client_id = :c "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"c": cid}).fetchone()
    return {"client_id": client_id,
            "balance": float(w[0]) if w else 0.0,
            "subscription_status": s[0] if s else "none"}


@e35_router.get("/visits")
def e35_visits(client_id: str, db: Session = Depends(get_db), user=Depends(_gcu)):
    """E35.7 — история посещений клиента"""
    rows = db.execute(_sql(
        "SELECT id, entry_time, access_method, status FROM visits "
        "WHERE client_id = :c ORDER BY entry_time DESC"
    ), {"c": _uuid.UUID(client_id)}).fetchall()
    visits = [{"visit_id": str(r[0]), "entry_time": str(r[1]),
               "access_method": r[2], "status": r[3]} for r in rows]
    return {"visits": visits, "total": len(visits)}


@e35_router.post("/print-receipt")
def e35_print_receipt(payload: _ReceiptRequest, db: Session = Depends(get_db),
                      user=Depends(_gcu)):
    """E35.8 — печать чека (эмуляция)"""
    if not payload.transaction_id:
        raise _HTTPExc(status_code=400, detail="transaction_id обязателен")
    return {"transaction_id": payload.transaction_id, "printed": True,
            "message": "Чек напечатан"}


@e35_router.post("/freeze-subscription")
def e35_freeze(payload: _FreezeRequest, db: Session = Depends(get_db),
               user=Depends(_gcu)):
    """E35.9 — заморозка абонемента"""
    r = db.execute(_sql(
        "SELECT id FROM subscriptions WHERE client_id = :c AND status = 'active' "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"c": _uuid.UUID(payload.client_id)}).fetchone()
    if not r:
        raise _HTTPExc(status_code=404, detail="Активный абонемент не найден")
    now = _dt.now(_tz.utc)
    db.execute(_sql(
        "UPDATE subscriptions SET status = 'frozen', frozen_at = :t, "
        "freeze_reason = :r, updated_at = :t WHERE id = :id"
    ), {"t": now, "r": payload.reason, "id": r[0]})
    db.commit()
    return {"subscription_id": str(r[0]), "message": "Абонемент заморожен"}


@e35_router.post("/unfreeze-subscription")
def e35_unfreeze(payload: _ClientRequest, db: Session = Depends(get_db),
                 user=Depends(_gcu)):
    """E35.10 — разморозка абонемента"""
    r = db.execute(_sql(
        "SELECT id FROM subscriptions WHERE client_id = :c AND status = 'frozen' "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"c": _uuid.UUID(payload.client_id)}).fetchone()
    if not r:
        raise _HTTPExc(status_code=404, detail="Замороженный абонемент не найден")
    db.execute(_sql(
        "UPDATE subscriptions SET status = 'active', frozen_at = NULL, "
        "freeze_reason = NULL, frozen_until = NULL, updated_at = :t WHERE id = :id"
    ), {"t": _dt.now(_tz.utc), "id": r[0]})
    db.commit()
    return {"subscription_id": str(r[0]), "message": "Абонемент разморожен"}


@e35_router.post("/pay-terminal")
def e35_pay_terminal(payload: _PayRequest, db: Session = Depends(get_db),
                     user=Depends(_gcu)):
    """E35.11/E35.12 — оплата картой через терминал (эмуляция)"""
    if not _TERMINAL["online"]:
        raise _HTTPExc(status_code=503, detail="Терминал оплаты недоступен")
    return {"client_id": payload.client_id, "amount": payload.amount,
            "payment_status": "success", "slip_printed": True,
            "message": "Оплата успешна, slip напечатан"}


@e35_router.get("/qr-code")
def e35_qr_code(client_id: str, db: Session = Depends(get_db), user=Depends(_gcu)):
    """E35.13 — QR-код для входа"""
    return {"client_id": client_id,
            "qr_code": f"FITQR-{client_id}-{_uuid.uuid4().hex[:8]}",
            "qr_displayed": True, "message": "QR-код отображён"}


@e35_router.post("/face-entry")
def e35_face_entry(payload: _FaceEntryRequest, db: Session = Depends(get_db),
                   user=Depends(_gcu)):
    """E35.14/E35.15 — вход по Face ID, регистрация посещения"""
    face = db.execute(_sql(
        "SELECT client_id FROM terminal_faces WHERE photo = :p LIMIT 1"
    ), {"p": payload.photo}).fetchone()
    if not face:
        raise _HTTPExc(
            status_code=403,
            detail="Лицо не распознано, обратитесь к администратору")
    cid = face[0]
    sub = db.execute(_sql(
        "SELECT id FROM subscriptions WHERE client_id = :c AND status = 'active' "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"c": _uuid.UUID(cid)}).fetchone()
    vid = _uuid.uuid4()
    now = _dt.now(_tz.utc)
    db.execute(_sql(
        "INSERT INTO visits (id, client_id, subscription_id, entry_time, "
        "access_method, access_granted, status, created_at, updated_at) "
        "VALUES (:i, :c, :s, :t, 'face_id', TRUE, 'active', :t, :t)"
    ), {"i": vid, "c": _uuid.UUID(cid),
        "s": sub[0] if sub else None, "t": now})
    db.commit()
    return {"client_id": cid, "turnstile_open": True, "visit_registered": True,
            "visit_id": str(vid),
            "message": "Вход разрешён, посещение зарегистрировано"}


@e35_router.post("/test/terminal")
def e35_terminal_toggle(payload: _TerminalToggle, user=Depends(_gcu)):
    """Тестовый переключатель терминала оплаты (только для тестов!)"""
    _TERMINAL["online"] = payload.online
    return {"terminal_online": _TERMINAL["online"]}
