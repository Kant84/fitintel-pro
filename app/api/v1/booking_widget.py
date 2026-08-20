"""E41: Online Booking Widget (ТЗ v3.2 §4.8).

Публичный виджет онлайн-записи на сайт клуба: конфигурация,
список услуг, свободные слоты, запись гостя (без регистрации),
проверка статуса и отмена по телефону, embed-сниппет.
"""
import json
import re
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

router = APIRouter(prefix="/booking-widget", tags=["booking-widget"])

_FMT = "%Y-%m-%d %H:%M:%S"
_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{9,}$")
_WORK_HOURS = range(9, 21)  # 09:00 - 20:00


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


def _get_settings(db, club_id):
    row = db.execute(
        text("SELECT * FROM widget_settings WHERE club_id=:c"), {"c": club_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Виджет не настроен")
    s = dict(row)
    if not s.get("is_enabled"):
        raise HTTPException(status_code=403, detail="Виджет отключён")
    return s


def _service_exists(db, service_id):
    try:
        key = uuid.UUID(str(service_id))
    except (ValueError, AttributeError):
        key = str(service_id)
    row = db.execute(
        text("SELECT id, name, price FROM services WHERE id=:i AND is_active=true"), {"i": key}
    ).mappings().fetchone()
    return dict(row) if row else None


def _get_booking(db, booking_id):
    row = db.execute(
        text("SELECT * FROM widget_bookings WHERE id=:i"), {"i": booking_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return dict(row)


class SettingsUpsert(BaseModel):
    club_id: str
    is_enabled: bool = True
    title: str = "Онлайн-запись"
    primary_color: str = "#4F46E5"
    logo_url: Optional[str] = None
    allowed_services: Optional[list] = None
    require_phone: bool = True


class BookRequest(BaseModel):
    service_id: str
    client_name: str
    client_phone: str
    slot_datetime: str
    comment: Optional[str] = None


class CancelRequest(BaseModel):
    phone: str


# ---------- публичные эндпоинты (без авторизации) ----------

@router.get("/public/{club_id}/config")
def public_config(club_id: str, db: Session = Depends(get_db)):
    s = _get_settings(db, club_id)
    return {"club_id": club_id, "title": s.get("title"), "primary_color": s.get("primary_color"),
            "logo_url": s.get("logo_url"), "require_phone": bool(s.get("require_phone"))}


@router.get("/public/{club_id}/services")
def public_services(club_id: str, db: Session = Depends(get_db)):
    s = _get_settings(db, club_id)
    allowed = None
    if s.get("allowed_services"):
        try:
            allowed = set(json.loads(s["allowed_services"]))
        except Exception:
            allowed = None
    rows = db.execute(
        text("SELECT id, name, price, duration_minutes FROM services WHERE is_active=true ORDER BY name")
    ).mappings().fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        if allowed is None or d["id"] in allowed:
            out.append(d)
    return out


@router.get("/public/{club_id}/slots")
def public_slots(club_id: str, service_id: str = Query(...), date: str = Query(...),
                 db: Session = Depends(get_db)):
    _get_settings(db, club_id)
    if not _service_exists(db, service_id):
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    busy_rows = db.execute(
        text("SELECT slot_datetime FROM widget_bookings WHERE service_id=:s AND slot_datetime LIKE :d AND status<>'cancelled'"),
        {"s": service_id, "d": date + "%"},
    ).fetchall()
    busy = {r[0] for r in busy_rows}
    slots = []
    for h in _WORK_HOURS:
        slot = f"{date} {h:02d}:00:00"
        slots.append({"datetime": slot, "free": slot not in busy})
    return {"date": date, "service_id": service_id, "slots": slots}


@router.post("/public/{club_id}/book", status_code=201)
def public_book(club_id: str, payload: BookRequest, db: Session = Depends(get_db)):
    _get_settings(db, club_id)
    if not _service_exists(db, payload.service_id):
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    if not _PHONE_RE.match(payload.client_phone or ""):
        raise HTTPException(status_code=400, detail="Некорректный телефон")
    busy = db.execute(
        text("SELECT id FROM widget_bookings WHERE service_id=:s AND slot_datetime=:t AND status<>'cancelled'"),
        {"s": payload.service_id, "t": payload.slot_datetime},
    ).fetchone()
    if busy:
        raise HTTPException(status_code=409, detail="Слот занят, выберите другой")
    bid = str(uuid.uuid4())
    _insert(db, "widget_bookings", {
        "id": bid, "club_id": club_id, "service_id": payload.service_id,
        "client_name": payload.client_name, "client_phone": payload.client_phone,
        "slot_datetime": payload.slot_datetime, "status": "new",
        "comment": payload.comment, "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"booking_id": bid, "status": "new", "message": "Запись создана, ожидайте подтверждения"}


@router.get("/public/{club_id}/booking/{booking_id}")
def public_booking_status(club_id: str, booking_id: str, db: Session = Depends(get_db)):
    b = _get_booking(db, booking_id)
    if b["club_id"] != club_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"booking_id": booking_id, "status": b["status"],
            "service_id": b["service_id"], "slot_datetime": b["slot_datetime"]}


@router.post("/public/{club_id}/booking/{booking_id}/cancel")
def public_cancel(club_id: str, booking_id: str, payload: CancelRequest, db: Session = Depends(get_db)):
    b = _get_booking(db, booking_id)
    if b["club_id"] != club_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if b["client_phone"] != payload.phone:
        raise HTTPException(status_code=403, detail="Телефон не совпадает")
    if b["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    db.execute(text("UPDATE widget_bookings SET status='cancelled' WHERE id=:i"), {"i": booking_id})
    db.commit()
    return {"message": "Запись отменена", "status": "cancelled"}


@router.get("/embed/{club_id}")
def embed_snippet(club_id: str, db: Session = Depends(get_db)):
    _get_settings(db, club_id)
    html = (
        '<div id="fitintel-booking" data-club="%s"></div>\n'
        '<script src="https://cdn.fitintel.pro/widget.js" async></script>'
    ) % club_id
    return {"club_id": club_id, "html": html}


# ---------- административные эндпоинты ----------

@router.post("/settings")
def upsert_settings(payload: SettingsUpsert, db: Session = Depends(get_db),
                    user=Depends(require_roles("admin"))):
    row = db.execute(
        text("SELECT id FROM widget_settings WHERE club_id=:c"), {"c": payload.club_id}
    ).fetchone()
    allowed = json.dumps(payload.allowed_services, ensure_ascii=False) if payload.allowed_services else None
    if row:
        db.execute(
            text("UPDATE widget_settings SET is_enabled=:e, title=:t, primary_color=:c, logo_url=:l, allowed_services=:a, require_phone=:r WHERE club_id=:cid"),
            {"e": 1 if payload.is_enabled else 0, "t": payload.title, "c": payload.primary_color,
             "l": payload.logo_url, "a": allowed, "r": 1 if payload.require_phone else 0,
             "cid": payload.club_id},
        )
    else:
        _insert(db, "widget_settings", {
            "id": str(uuid.uuid4()), "club_id": payload.club_id,
            "is_enabled": 1 if payload.is_enabled else 0, "title": payload.title,
            "primary_color": payload.primary_color, "logo_url": payload.logo_url,
            "allowed_services": allowed,
            "require_phone": 1 if payload.require_phone else 0,
            "created_at": _fmt(datetime.now()),
        })
    db.commit()
    return {"message": "Настройки виджета сохранены", "club_id": payload.club_id}


@router.get("/settings/{club_id}")
def get_settings(club_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.execute(
        text("SELECT * FROM widget_settings WHERE club_id=:c"), {"c": club_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Виджет не настроен")
    return dict(row)


@router.get("/bookings")
def list_bookings(club_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM widget_bookings WHERE 1=1"
    params = {}
    if club_id:
        q += " AND club_id=:c"
        params["c"] = club_id
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/bookings/{booking_id}/confirm")
def confirm_booking(booking_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    b = _get_booking(db, booking_id)
    if b["status"] == "confirmed":
        raise HTTPException(status_code=400, detail="Запись уже подтверждена")
    if b["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Запись отменена")
    db.execute(text("UPDATE widget_bookings SET status='confirmed' WHERE id=:i"), {"i": booking_id})
    db.commit()
    return {"message": "Запись подтверждена", "status": "confirmed"}


@router.post("/bookings/{booking_id}/cancel")
def admin_cancel(booking_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    b = _get_booking(db, booking_id)
    if b["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    db.execute(text("UPDATE widget_bookings SET status='cancelled' WHERE id=:i"), {"i": booking_id})
    db.commit()
    return {"message": "Запись отменена", "status": "cancelled"}
