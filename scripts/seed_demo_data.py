"""Скрипт демо-данных FitIntel Pro (Волна 5).

ЗАПУСК НА СЕРВЕРЕ (внутри контейнера api):
    docker cp scripts/seed_demo_data.py deploy-api-1:/app/scripts/seed_demo_data.py
    docker exec -w /app deploy-api-1 python scripts/seed_demo_data.py

Что делает: берёт СУЩЕСТВУЮЩИХ тренеров (TrainerProfile) и клиентов (Client)
и добавляет:
  • УСЛУГИ (10 шт): групповые занятия с расписанием по дням недели (schedule JSON),
    персоналки, массаж, сауна/солярий — с привязкой к тренерам;
  • фото тренерам, у кого нет (picsum — внешние URL для демо);
  • ЗАПИСИ: 15–25 случайных записей клиентов на ближайшие 7 дней
    (слоты из расписаний услуг, статусы BOOKED/CONFIRMED/PAID).

Идемпотентно: услуги с тем же именем не дублируются, записи — проверка
по (client, service, datetime). Повторный запуск безопасен.
"""
import random
import sys
import uuid
from datetime import date, datetime, time as dtime, timedelta

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app.db.session import SessionLocal          # noqa: E402
from app.models.service import Service, ServiceBooking   # noqa: E402
from app.models.trainer import TrainerProfile    # noqa: E402
from app.models.client import Client             # noqa: E402

random.seed(20261009)  # воспроизводимо: при каждом запуске «те же случайные»


# name, category, price, duration, capacity, days, slots
SERVICES = [
    ("Здоровая спина",        "AEROBICS",          500,  55, 12, [0, 2, 4],        ["10:00", "18:00"]),
    ("Йога-студия",           "AEROBICS",          600,  60, 15, [0, 4],           ["08:00", "20:00"]),
    ("Степ-аэробика",         "AEROBICS",          550,  45, 14, [1, 3],           ["19:00"]),
    ("Кроссфит",              "DANCE",             700,  60, 10, [1, 3, 5],        ["07:30", "19:30"]),
    ("Танцы (латина)",        "DANCE",             650,  60, 12, [2, 4],           ["20:00"]),
    ("Детское плавание 7–9",  "POOL",              550,  45, 8,  [2, 4, 6],        ["16:00"]),
    ("Аквааэробика",          "POOL",              600,  50, 10, [0, 3],           ["11:00"]),
    ("Персональная тренировка", "PERSONAL_TRAINER", 1500, 60, 1, [0, 1, 2, 3, 4],  ["09:00", "12:00", "15:00", "17:00", "20:00"]),
    ("Массаж спортивный",     "MASSAGE",           1800, 60, 1,  [0, 1, 2, 3, 4, 5], ["11:00", "14:00", "18:00"]),
    ("Сауна / Солярий",       "SAUNA",             400,  60, 4,  [0, 1, 2, 3, 4, 5, 6], ["10:00", "13:00", "16:00", "21:00"]),
]



def _ensure_booking_columns(db):
    """Боевая таблица service_bookings могла создаться до Волны 5 —
    гарантируем notes + колонки жизненного цикла (идемпотентно)."""
    from sqlalchemy import text as _t
    try:
        if db.bind.dialect.name == "postgresql":
            cols = {r[0] for r in db.execute(_t(
                "SELECT column_name FROM information_schema.columns WHERE table_name='service_bookings'"))}
            ddls = {"notes": "ALTER TABLE service_bookings ADD COLUMN notes TEXT",
                    "confirmed_at": "ALTER TABLE service_bookings ADD COLUMN confirmed_at TIMESTAMP",
                    "paid_at": "ALTER TABLE service_bookings ADD COLUMN paid_at TIMESTAMP",
                    "reminded_at": "ALTER TABLE service_bookings ADD COLUMN reminded_at TIMESTAMP",
                    "pinged_at": "ALTER TABLE service_bookings ADD COLUMN pinged_at TIMESTAMP",
                    "price": "ALTER TABLE service_bookings ADD COLUMN price NUMERIC(10,2)",
                    "source": "ALTER TABLE service_bookings ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'api'"}
            for col, ddl in ddls.items():
                if col not in cols:
                    db.execute(_t(ddl))
            db.commit()
    except Exception as e:
        db.rollback()
        print("ensure service_bookings:", str(e)[:120])


def main():
    db = SessionLocal()
    try:
        _ensure_booking_columns(db)
        trainers = db.query(TrainerProfile).all()
        clients = db.query(Client).filter(Client.is_active.is_(True)).limit(60).all()
        if not clients:
            print("Нет клиентов в базе — записи не создать. Услуги создам.")
        print(f"В базе: тренеров {len(trainers)}, клиентов (до 60) {len(clients)}")

        # фото тренерам, у кого нет
        photos = 0
        for i, tp in enumerate(trainers):
            if not getattr(tp, "photo_url", None):
                try:
                    tp.photo_url = f"https://picsum.photos/seed/trainer{i+1}/400/400"
                    photos += 1
                except Exception:
                    pass
        db.commit()
        if photos:
            print(f"Фото добавлено тренерам: {photos}")

        # услуги
        created = 0
        service_objs = []
        for idx, (name, cat, price, dur, cap, days, slots) in enumerate(SERVICES):
            sv = db.query(Service).filter_by(name=name).first()
            if not sv:
                trainer = trainers[idx % len(trainers)] if trainers else None
                # ВАЖНО: services.trainer_id -> users.id (FK), НЕ id профиля тренера
                tid = getattr(trainer, "user_id", None) if trainer else None
                sv = Service(
                    name=name, category=cat, price=price, duration_minutes=dur,
                    max_capacity=cap, is_active=True,
                    trainer_id=tid,
                    schedule={"days": days,
                              "time_slots": [{"time": t, "capacity": cap} for t in slots]},
                )
                db.add(sv)
                db.flush()
                created += 1
            service_objs.append(sv)
        db.commit()
        print(f"Услуг: создано новых {created}, всего в выборке {len(service_objs)}")

        # записи на ближайшие 7 дней
        bookings = 0
        today = date.today()
        for _ in range(25):
            if not clients:
                break
            sv = random.choice(service_objs)
            sched = sv.schedule or {}
            days = sched.get("days") or list(range(7))
            slots = sched.get("time_slots") or []
            if not slots:
                continue
            # ближайший подходящий день
            for add in range(1, 8):
                d = today + timedelta(days=add)
                if d.weekday() in days:
                    break
            else:
                continue
            slot = random.choice(slots)
            t = slot.get("time", "12:00")
            when = datetime.combine(d, dtime(int(t[:2]), int(t[3:])))
            c = random.choice(clients)
            exists = db.query(ServiceBooking).filter_by(
                service_id=sv.id, client_id=str(c.id), booking_date=when).first()
            if exists:
                continue
            db.add(ServiceBooking(
                service_id=sv.id, client_id=str(c.id), booking_date=when,
                status=random.choices(["BOOKED", "CONFIRMED", "PAID"], weights=[5, 3, 2])[0],
                source=random.choice(["MAX", "reception"])))
            bookings += 1
        db.commit()
        print(f"Записей создано: {bookings}")
        print("Готово. Проверьте: Расписание (Занятия по дням / Тренеры / Записи), Услуги, бот.")
    finally:
        db.close()


if __name__ == "__main__":
    main()