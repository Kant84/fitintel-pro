"""Политика права входа: бот /qr и турникет используют ОДНУ функцию.

Основания (не «единый вход» — любое из):
  1. ACTIVE-абонемент с остатком визитов (логика как в access_service);
  2. оплаченное бронирование услуги (ServiceBooking.status=PAID),
     начало в пределах ±QR_ACCESS_WINDOW_HOURS (параметр клуба).
"""
from datetime import datetime, timezone, timedelta, date

from sqlalchemy.orm import Session

from app.api.v1.club_params import get_param_int
from app.models.service import Service, ServiceBooking
from app.models.subscription import Subscription


def _aware(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is None:
        return dt.astimezone()
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


def entry_reasons(db: Session, client_id: str, at: datetime | None = None) -> list:
    """Список оснований для входа. Пусто -> QR не выдаём, турникет не пускает."""
    at = _aware(at) or datetime.now(timezone.utc)
    reasons = []
    sub = _active_subscription(db, client_id)
    if sub:
        left = "∞" if (sub.is_unlimited or sub.visit_limit is None) \
            else str(sub.visit_limit - sub.visits_used)
        reasons.append(f"Абонемент активен (осталось визитов: {left})")
    window = get_param_int("QR_ACCESS_WINDOW_HOURS", 1)
    lo, hi = at - timedelta(hours=window), at + timedelta(hours=window)
    rows = (db.query(ServiceBooking, Service)
            .join(Service, ServiceBooking.service_id == Service.id)
            .filter(ServiceBooking.client_id == str(client_id),
                    ServiceBooking.status == "PAID",
                    ServiceBooking.booking_date >= lo,
                    ServiceBooking.booking_date <= hi)
            .all())
    for b, s in rows:
        reasons.append(f"Оплаченное занятие «{s.name}» в {b.booking_date.strftime('%H:%M')}")
    return reasons


def can_enter(db: Session, client_id: str, at: datetime | None = None) -> bool:
    return bool(entry_reasons(db, client_id, at))