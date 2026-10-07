"""Политика права входа: бот /qr и турникет используют ОДНУ функцию.

Основания (не «единый вход» — любое из):
  1. ACTIVE-абонемент с остатком визитов (логика как в access_service);
  2. оплаченное бронирование услуги (ServiceBooking.status=PAID),
     начало в пределах ±QR_ACCESS_WINDOW_HOURS (параметр клуба).
"""
from datetime import datetime, timezone, timedelta, date

from sqlalchemy import text as _sql_text
from sqlalchemy.orm import Session

from app.api.v1.club_params import get_param, get_param_int
from app.models.service import Service, ServiceBooking
from app.models.subscription import Subscription


def _aware(dt):
    # naive datetime из БД — это UTC (sqlite-адаптер срезает tz, сохраняя UTC).
    # ВАЖНО: replace, не astimezone — иначе naive трактуется как LOCAL (+3ч).
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _active_subscription(db: Session, client_id: str):
    today = date.today()
    sub = (db.query(Subscription)
           .filter(Subscription.client_id == str(client_id),
                   Subscription.is_active.is_(True),
                   Subscription.status == "ACTIVE",
                   Subscription.end_date >= today)
           .first())
    if not sub:
        return None
    if not sub.is_unlimited and sub.visit_limit is not None:
        if sub.visits_used >= sub.visit_limit:
            return None
    return sub


def _day_bounds(dt: datetime) -> tuple:
    """00:00:00 и 23:59:59 даты dt (локальные)."""
    d = dt.date()
    start = datetime(d.year, d.month, d.day, tzinfo=dt.tzinfo)
    return start, start + timedelta(days=1) - timedelta(seconds=1)


def _booking_grants_entry(b, svc, at: datetime,
                          before_h: int, after_h: int, until_close: bool,
                          gym_full_day: bool) -> bool:
    """Одна оплаченная бронь даёт вход в момент at?"""
    start = _aware(b.booking_date)
    if gym_full_day and svc is not None and str(getattr(svc, "category", "")) == "GYM_ACCESS":
        lo, hi = _day_bounds(start)          # разовый зал: весь день оплаты
    else:
        lo = start - timedelta(hours=before_h)
        hi = (_day_bounds(start)[1] if until_close
              else start + timedelta(hours=after_h))
    return lo <= at <= hi


def entry_reasons(db: Session, client_id: str, at: datetime | None = None) -> list:
    """Список оснований для входа. Пусто -> QR не выдаём, турникет не пускает.
    Окно входа на занятие — ассимметричное и настраивается клубом:
    BEFORE часов до + AFTER после, либо STAY_UNTIL_CLOSE (до конца дня).
    Разовый зал (GYM_ACCESS) — весь день оплаты (GYM_ACCESS_FULL_DAY)."""
    at = _aware(at) or datetime.now(timezone.utc)
    reasons = []
    sub = _active_subscription(db, client_id)
    if sub:
        left = "∞" if (sub.is_unlimited or sub.visit_limit is None) \
            else str(sub.visit_limit - sub.visits_used)
        reasons.append(f"Абонемент активен (осталось визитов: {left})")
    before_h = get_param_int("ENTRY_WINDOW_BEFORE_HOURS", 1)
    after_h = get_param_int("ENTRY_WINDOW_AFTER_HOURS", 1)
    until_close = str(get_param("ENTRY_STAY_UNTIL_CLOSE", "false")).lower() == "true"
    gym_full_day = str(get_param("GYM_ACCESS_FULL_DAY", "true")).lower() == "true"
    # широкий охват выборки: фильтр точный — в Python (окна ассимметричные).
    # Основания считаем и по своим броням, и по броням детей (родитель приводит ребёнка).
    me = str(client_id).replace("-", "")
    # дети — raw-SQL: атрибута parent_id в модели Client нет (колонка — ALTER-ом)
    try:
        kids = [r[0] for r in db.execute(
            _sql_text("SELECT id FROM clients WHERE parent_id = :p"),
            {"p": me}).fetchall()]
    except Exception:
        kids = []
    family = [me] + [str(k).replace("-", "") for k in kids]
    lo_scan, hi_scan = at - timedelta(hours=48), at + timedelta(days=2)
    rows = (db.query(ServiceBooking, Service)
            .join(Service, ServiceBooking.service_id == Service.id)
            .filter(ServiceBooking.client_id.in_(family),
                    ServiceBooking.status == "PAID",
                    ServiceBooking.booking_date >= lo_scan,
                    ServiceBooking.booking_date <= hi_scan)
            .all())
    for b, svc in rows:
        if _booking_grants_entry(b, svc, at, before_h, after_h,
                                 until_close, gym_full_day):
            t = _aware(b.booking_date).strftime("%H:%M")
            whose = "" if str(b.client_id).replace("-", "") == me else " (ребёнок)"
            reasons.append(f"Оплаченное занятие «{svc.name}» в {t}{whose}")
    return reasons


def can_enter(db: Session, client_id: str, at: datetime | None = None) -> bool:
    return bool(entry_reasons(db, client_id, at))