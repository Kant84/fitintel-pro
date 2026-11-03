"""Напоминания об окончании аренды шкафчиков (Kerong).
Beat: каждый час. Аренды с rented_until <= now()+72ч и reminder_sent=false
-> уведомление клиенту (канал по настройкам «Клиенту»), затем пометка напоминания."""
from celery import shared_task
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.client_notify_service import ClientNotifyService, ensure_client_notify_columns


@shared_task(name="app.tasks.locker_rental_reminders")
def locker_rental_reminders():
    db = SessionLocal()
    try:
        ensure_client_notify_columns(db)
        db.execute(text("ALTER TABLE locker_rentals ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE"))
        db.commit()
        rows = db.execute(text("""
            SELECT client_id::text, cu_board_id, lock_number, rented_until
            FROM locker_rentals
            WHERE is_active AND rented_until IS NOT NULL
              AND rented_until <= now() + interval '72 hours'
              AND (reminder_sent IS NULL OR reminder_sent = FALSE)
            LIMIT 100""")).fetchall()
        sent = 0
        for cid, cu, ln, until in rows:
            date_str = str(until)[:10] if until else ""
            msg = (f"Срок аренды ячейки {cu}/{ln} заканчивается {date_str}. "
                   f"Продлите аренду на ресепшене или освободите ячейку.")
            res = ClientNotifyService(db).send(cid, "locker_rental_expiry", msg)
            if res.get("ok"):
                db.execute(text("UPDATE locker_rentals SET reminder_sent=TRUE "
                                "WHERE client_id=:c AND cu_board_id=:u AND lock_number=:l AND is_active"),
                           {"c": cid, "u": cu, "l": ln})
                db.commit()
                sent += 1
        return {"scanned": len(rows), "sent": sent}
    finally:
        db.close()
