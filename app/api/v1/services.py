#app\api\v1\services.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission, require_roles
from app.db.session import get_db
from app.models.service import Service, ServiceBooking
from app.models.user import User
# --- схемы локально (ваш app/schemas/service.py в репо отличается от присланного:
#     ServiceOut отсутствует). Самодостаточность убирает класс ImportError при дрейфе схем.
from pydantic import BaseModel, ConfigDict


class ServiceBookingCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    client_id: UUID
    booking_date: datetime
    notes: Optional[str] = None
    source: Optional[str] = None


class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: Optional[str] = None
    category: str = "OTHER"
    price: float = 0.0
    duration_minutes: int = 60
    max_capacity: int = 1
    is_active: bool = True
    trainer_id: Optional[UUID] = None
    schedule: Optional[dict] = None


class ServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    duration_minutes: Optional[int] = None
    max_capacity: Optional[int] = None
    is_active: Optional[bool] = None
    trainer_id: Optional[UUID] = None
    schedule: Optional[dict] = None


router = APIRouter()

# --- Волна 5: колонки жизненного цикла брони (idempotent, raw-SQL как в branding.py) ---
# Импорты club_params — ЛЕНИВЫЕ (внутри функций): иначе возможен цикл на старте.
from sqlalchemy import text as _text

_BCOLS_DONE = False


def _w5_engine():
    for mod in ("app.db.session", "app.core.database", "app.database"):
        try:
            m = __import__(mod, fromlist=["engine"])
            return m.engine
        except Exception:
            continue
    raise RuntimeError("services(W5): engine not found")


def _ensure_booking_cols():
    """Добавляет service_bookings: confirmed_at/paid_at/reminded_at/pinged_at/price/source."""
    global _BCOLS_DONE
    if _BCOLS_DONE:
        return
    try:
        with _w5_engine().begin() as c:
            if _w5_engine().dialect.name == "postgresql":
                for ddl in ("ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP",
                            "ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP",
                            "ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMP",
                            "ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS pinged_at TIMESTAMP",
                            "ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS price NUMERIC(10,2)",
                            "ALTER TABLE service_bookings ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'api'"):
                    c.execute(_text(ddl))
            else:
                cols = {r[1] for r in c.execute(_text("PRAGMA table_info(service_bookings)"))}
                for col, ddl in {
                    "confirmed_at": "ALTER TABLE service_bookings ADD COLUMN confirmed_at TIMESTAMP",
                    "paid_at": "ALTER TABLE service_bookings ADD COLUMN paid_at TIMESTAMP",
                    "reminded_at": "ALTER TABLE service_bookings ADD COLUMN reminded_at TIMESTAMP",
                    "pinged_at": "ALTER TABLE service_bookings ADD COLUMN pinged_at TIMESTAMP",
                    "price": "ALTER TABLE service_bookings ADD COLUMN price NUMERIC(10,2)",
                    "source": "ALTER TABLE service_bookings ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'api'",
                }.items():
                    if col not in cols:
                        c.execute(_text(ddl))
        _BCOLS_DONE = True
    except Exception:
        pass  # таблица ещё не создана (старт/тесты) — повторим при следующем вызове


def _ensure_rating_col(db: Session):
    """clients.rating — лениво и диалектно-нейтрально ТОЙ ЖЕ сессией
    (тестовая sqlite строит таблицы из модели, где rating нет — вот и ALTER)."""
    try:
        if db.bind.dialect.name == "postgresql":
            db.execute(_text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS "
                             "rating DOUBLE PRECISION DEFAULT 5.0"))
        else:
            cols = {r[1] for r in db.execute(_text("PRAGMA table_info(clients)"))}
            if "rating" not in cols:
                db.execute(_text("ALTER TABLE clients ADD COLUMN rating FLOAT DEFAULT 5.0"))
        db.commit()
    except Exception:
        db.rollback()


def _deps(db: Session = Depends(get_db)):
    _ensure_booking_cols()
    _ensure_rating_col(db)
    return db


def _apply_rating(db: Session, client_id: str, delta: float):
    """Рейтинг клиента: clamp [1.0, 5.0]. Читаем/пишем ТОЙ ЖЕ сессией (тесты!).
    Кламп в Python — диалектно-нейтрально (sqlite max() != Postgres MAX())."""
    uid = str(client_id).replace("-", "")
    # replace('-','') — формат-хранения-нейтрально: hex (контейнер) и dashed (локально)
    row = db.execute(_text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                     {"i": uid}).first()
    cur = float(row[0]) if row and row[0] is not None else 5.0
    new = min(5.0, max(1.0, cur + delta))
    db.execute(_text("UPDATE clients SET rating = :r WHERE replace(id, '-', '') = :i"),
               {"r": new, "i": uid})
    db.commit()


# ============================ SERVICES ============================

@router.get("/services")
def list_services(
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Service)
    if active_only:
        q = q.filter(Service.is_active.is_(True))
    if category:
        q = q.filter(Service.category == category)
    return q.order_by(Service.name).all()


@router.post("/services", status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_permission("services.create")),
):
    svc = Service(**body.model_dump())
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


@router.get("/services/trainer-schedule")
def get_trainer_schedule(
    trainer_id: Optional[UUID] = Query(None),
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Расписание тренеров: ближайшие активные записи."""
    q = db.query(ServiceBooking).join(Service).filter(
        Service.trainer_id.isnot(None),
        ServiceBooking.status == "BOOKED",
        ServiceBooking.booking_date >= datetime.now(timezone.utc),
    )
    if trainer_id:
        q = q.filter(Service.trainer_id == trainer_id)
    rows = q.order_by(ServiceBooking.booking_date).limit(100).all()
    out = []
    for b in rows:
        out.append({
            "id": str(b.id),
            "booking_date": b.booking_date.isoformat() if b.booking_date else None,
            "status": b.status,
            "notes": b.notes,
            "client_name": (b.client.first_name + " " + (b.client.last_name or "")) if b.client else None,
            "service_name": b.service.name if b.service else None,
            "trainer_name": (b.service.trainer.full_name if b.service and b.service.trainer else None),
        })
    return out




# --- Волна 5: жизненный цикл брони (фиксированные пути — ВЫШЕ /{service_id}) ---
@router.get("/services/bookings/upcoming")
def upcoming_bookings(
    db: Session = Depends(_deps),
    current_user: User = Depends(require_permission("bookings.read")),
):
    """Ближайшие активные брони (десктоп + свип)."""
    rows = (db.query(ServiceBooking)
            .filter(ServiceBooking.status.in_(["BOOKED", "CONFIRMED", "PAID"]),
                    ServiceBooking.booking_date >= datetime.now(timezone.utc) - timedelta(hours=2))
            .order_by(ServiceBooking.booking_date)
            .limit(200).all())
    return [{
        "id": str(b.id), "service_id": str(b.service_id), "client_id": str(b.client_id),
        "booking_date": b.booking_date.isoformat() if b.booking_date else None,
        "status": b.status, "price": b.price,
        "client_name": (b.client.first_name + " " + (b.client.last_name or "")) if b.client else None,
        "service_name": b.service.name if b.service else None,
        "confirmed_at": b.confirmed_at.isoformat() if b.confirmed_at else None,
        "paid_at": b.paid_at.isoformat() if b.paid_at else None,
    } for b in rows]


@router.get("/services/bookings/client/{client_id}")
def client_bookings(
    client_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Записи клиента (бот «Мои записи», десктоп)."""
    rows = (db.query(ServiceBooking)
            .filter(ServiceBooking.client_id == str(client_id))
            .order_by(ServiceBooking.booking_date.desc())
            .limit(50).all())
    return [{
        "id": str(b.id), "booking_date": b.booking_date.isoformat() if b.booking_date else None,
        "status": b.status, "price": b.price, "service_name": b.service.name if b.service else None,
    } for b in rows]



@router.get("/services/{service_id}", )
def get_service(
    service_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    svc = db.get(Service, service_id)
    if not svc:
        raise HTTPException(404, "Service not found")
    return svc


@router.patch("/services/{service_id}", )
def update_service(
    service_id: UUID,
    body: ServiceUpdate,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_permission("services.update")),
):
    svc = db.get(Service, service_id)
    if not svc:
        raise HTTPException(404, "Service not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(svc, k, v)
    db.commit()
    db.refresh(svc)
    return svc


@router.delete("/services/{service_id}", status_code=204)
def delete_service(
    service_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_permission("services.delete")),
):
    svc = db.get(Service, service_id)
    if not svc:
        raise HTTPException(404, "Service not found")
    svc.is_active = False
    db.commit()


# ============================ BOOKINGS ============================

@router.post("/services/{service_id}/book", status_code=status.HTTP_201_CREATED)
def book_service(
    service_id: UUID,
    booking: ServiceBookingCreate,
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Записать клиента на услугу."""
    svc = db.get(Service, service_id)
    if not svc or not svc.is_active:
        raise HTTPException(404, "Service not found or inactive")

    new_booking = ServiceBooking(
        service_id=service_id,
        client_id=booking.client_id,
        booking_date=booking.booking_date,
        notes=booking.notes,
        status="BOOKED",
        source=getattr(booking, "source", None) or "api",
    )
    db.add(new_booking)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Booking already exists for this date/time")

    db.refresh(new_booking)
    return svc  # фронт ожидает ServiceOut


@router.get("/services/{service_id}/availability")
def check_availability(
    service_id: UUID,
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Проверка доступности: сколько мест осталось на дату."""
    svc = db.get(Service, service_id)
    if not svc:
        raise HTTPException(404, "Service not found")
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    day_of_week = target.weekday()
    schedule = svc.schedule or {}
    if not schedule.get("days") or day_of_week not in schedule["days"]:
        return {"available": False, "reason": "not_scheduled_day", "slots": []}

    time_slots = schedule.get("time_slots", [])
    booked = db.query(ServiceBooking).filter(
        ServiceBooking.service_id == service_id,
        ServiceBooking.booking_date >= datetime.combine(target, datetime.min.time()),
        ServiceBooking.booking_date < datetime.combine(target + timedelta(days=1), datetime.min.time()),
        ServiceBooking.status.in_(["BOOKED", "COMPLETED"]),
    ).all()
    booked_hours = {b.booking_date.strftime("%H:%M") for b in booked}

    slots = []
    for slot in time_slots:
        time_str = slot.get("time", "")
        cap = slot.get("capacity", svc.max_capacity)
        left = max(0, cap - sum(1 for b in booked if b.booking_date.strftime("%H:%M") == time_str))
        slots.append({"time": time_str, "capacity": cap, "left": left, "available": left > 0})

    return {
        "available": any(s["available"] for s in slots),
        "date": date,
        "slots": slots,
    }


@router.post("/services/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Отмена записи — окно CANCEL_WINDOW_HOURS (параметр клуба, дефолт 24)."""
    booking = db.get(ServiceBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != "BOOKED":
        raise HTTPException(400, "Only BOOKED can be cancelled")

    from app.api.v1.club_params import get_param_int
    hours = get_param_int("CANCEL_WINDOW_HOURS", 24)
    bd = booking.booking_date
    if getattr(bd, "tzinfo", None) is None:
        bd = bd.replace(tzinfo=timezone.utc)   # naive из БД = UTC
    time_diff = bd - datetime.now(timezone.utc)
    if time_diff < timedelta(hours=hours):
        raise HTTPException(
            400,
            f"Отмена возможна только за {hours} часов до начала",
        )
    booking.status = "CANCELLED"
    db.commit()
    return {"status": "cancelled"}


# --- Волна 5: жизненный цикл брони ---

@router.post("/services/bookings/{booking_id}/confirm")
def confirm_booking(
    booking_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(get_current_user),
):
    """Клиент подтверждает бронь (кнопка в MAX)."""
    booking = db.get(ServiceBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != "BOOKED":
        raise HTTPException(409, f"Статус {booking.status} не требует подтверждения")
    booking.status = "CONFIRMED"
    booking.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "CONFIRMED"}


@router.post("/services/bookings/{booking_id}/pay")
def pay_booking(
    booking_id: UUID,
    price: Optional[float] = None,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_roles("admin", "owner", "reception", "cashier")),
):
    """Касса отметила оплату (нал/карта/СБП) — бронь становится основанием для входа."""
    booking = db.get(ServiceBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status not in ("BOOKED", "CONFIRMED"):
        raise HTTPException(409, "Оплатить можно только активную бронь")
    booking.status = "PAID"
    booking.paid_at = datetime.now(timezone.utc)
    if price is not None:
        booking.price = price
    db.commit()
    return {"status": "PAID"}


@router.post("/services/bookings/{booking_id}/no-show")
def no_show_booking(
    booking_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_roles("admin", "owner", "reception")),
):
    """Не пришёл без предупреждения: NO_SHOW, рейтинг -0.5."""
    booking = db.get(ServiceBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status not in ("CONFIRMED", "PAID"):
        raise HTTPException(409, "No-show: только подтверждённые/оплаченные")
    booking.status = "NO_SHOW"
    _apply_rating(db, str(booking.client_id), -0.5)
    return {"status": "NO_SHOW"}


@router.post("/services/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: UUID,
    db: Session = Depends(_deps),
    current_user: User = Depends(require_roles("admin", "owner", "reception", "trainer")),
):
    """Занятие состоялось: PAID -> COMPLETED, рейтинг +0.1."""
    booking = db.get(ServiceBooking, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status != "PAID":
        raise HTTPException(409, "Завершить можно только оплаченную бронь")
    booking.status = "COMPLETED"
    _apply_rating(db, str(booking.client_id), +0.1)
    return {"status": "COMPLETED"}


@router.post("/services/bookings/sweep")
def run_booking_sweep(
    db: Session = Depends(_deps),
    current_user: User = Depends(require_roles("admin", "owner")),
):
    """Ручной запуск свипа (шедулер дёргает сервис напрямую)."""
    from app.services.booking_sweep import sweep
    return sweep()