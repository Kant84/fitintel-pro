# tools/demo/demo_stats_fill.py  (v2.1, 08.11.2026)
"""Бэкфилл демо-статистики: визиты + платежи за последние N дней ОТ СЕГОДНЯ.

Свойства:
- даты от текущего дня (перед каждым демо просто перезапустите — статистика
  Главной, тепловой карты и ML не "проседает");
- ИДЕМПОТЕНТЕН: перед заливкой дня X удаляет свои же записи за день X
  (пометка access_device_id/notes = 'DEMO_FILL'), повторные запуски безопасны;
- работает ТОЛЬКО с фейковыми LT-клиентами (+7999LT%%) — реальным клиентам
  ничего не отправляется;
- платежи: CHECK-совместимые значения (RUB/INCOME/SUBSCRIPTION/COMPLETED).

Запуск (внутри контейнера api):
    docker cp tools/demo/demo_stats_fill.py deploy-api-1:/tmp/fill.py
    docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T api \
        env PYTHONPATH=/app python /tmp/fill.py --days 60 --per-day 140

Маркер успеха: FILL_DONE visits=... payments=...
"""
import argparse, random
from datetime import datetime, timedelta
from sqlalchemy import text
from app.db.session import SessionLocal

MARK = "DEMO_FILL"

def defaults(db, table):
    cols = db.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name=:t AND is_nullable='NO' AND column_default IS NULL"""),
        {"t": table}).all()
    vals = {}
    for name, dtype in (cols or []):
        d = (dtype or "").lower()
        if "timestamp" in d or d == "date": vals[name] = "now()"
        elif d in ("integer", "bigint", "smallint", "numeric", "real", "double precision"): vals[name] = "0"
        elif d == "boolean": vals[name] = "false"
        elif "uuid" in d: vals[name] = "gen_random_uuid()"
        else: vals[name] = "'DEMO'"
    return vals

def sample_col(db, table, col, fallback):
    try:
        rows = db.execute(text(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL LIMIT 8")).all()
        vals = [r[0] for r in rows if r[0] and str(r[0]) != 'DEMO']
        return random.choice(vals) if vals else fallback
    except Exception:
        return fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--per-day", type=int, default=140)
    ap.add_argument("--payments-every", type=float, default=0.2, help="вероятность платежа на визит")
    args = ap.parse_args()

    db = SessionLocal()
    random.seed()
    today = datetime.now().date()
    now = datetime.now()

    # LT-клиенты с активным абонементом
    clients = db.execute(text("""
        SELECT c.id FROM clients c
        WHERE c.is_active AND c.deleted_at IS NULL AND c.phone LIKE '+7999LT%%'
          AND EXISTS (SELECT 1 FROM subscriptions s WHERE s.client_id = c.id AND s.is_active)
        LIMIT 3000""")).all()
    if not clients:
        print("Нет LT-клиентов! Сначала: tools/loadtest/generate_data.py --clients 3000")
        return
    ids = [str(r[0]) for r in clients]

    method  = sample_col(db, "visits",  "access_method", "MANUAL")
    status  = sample_col(db, "visits",  "status", "COMPLETED")
    zone    = sample_col(db, "visits",  "zone", "GYM")
    pmethod = sample_col(db, "payments", "payment_method", "CARD")

    v = defaults(db, "visits")
    v.update({"id": "gen_random_uuid()", "client_id": ":cid", "entry_time": ":et", "exit_time": ":xt",
              "status": "'%s'" % status, "access_granted": "true",
              "access_method": "'%s'" % method, "zone": "'%s'" % zone,
              "access_device_id": "'%s'" % MARK, "created_at": ":et", "updated_at": ":xt"})
    if "notes" in v: v["notes"] = "'%s'" % MARK

    # CHECK-совместимые значения (см. app/models/payment.py)
    p = defaults(db, "payments")
    p.update({"id": "gen_random_uuid()", "client_id": ":cid", "amount": ":amt",
              "currency": "'RUB'", "payment_method": "'%s'" % pmethod,
              "payment_direction": "'INCOME'", "payment_category": "'SUBSCRIPTION'",
              "status": "'COMPLETED'", "paid_at": ":et", "created_at": ":et"})
    if "notes" in p: p["notes"] = "'%s'" % MARK
    p.pop("external_payment_id", None)   # пусть будет NULL, а не 'DEMO'

    vi = pi = perr = 0
    for d in range(args.days, 0, -1):
        day = today - timedelta(days=d - 1)          # v2: d=1 = СЕГОДНЯ
        # идемпотентность: чистим свой же день
        db.execute(text("DELETE FROM visits WHERE access_device_id=:m AND entry_time::date=:d"),
                   {"m": MARK, "d": day})
        db.execute(text("DELETE FROM payments WHERE notes=:m AND created_at::date=:d"),
                   {"m": MARK, "d": day})
        db.commit()

        dow = day.weekday()
        n = int(args.per_day * (1.3 if dow >= 5 else 1.0))
        for _ in range(n):
            if dow >= 5:
                hour = random.choices([10,11,12,13,14,15,16,17,18], [1,2,3,3,3,2,2,1,1])[0]
            else:
                hour = random.choices([6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                                      [1,1,2,2,2,2,3,3,4,4,5,7,8,8,7,3])[0]
            et = datetime(day.year, day.month, day.day, hour, random.randint(0, 59))
            dur = random.randint(35, 130)
            xt = et + timedelta(minutes=dur)
            st = status
            if xt > now:           # ещё в клубе: без выхода, статус ACTIVE
                xt = None
                st = "ACTIVE"
            cid = random.choice(ids)
            try:
                vv = dict(v); vv["status"] = "'%s'" % st
                if xt is None:
                    vv["updated_at"] = "now()"   # ACTIVE-визит: без exit_time, но updated_at обязателен
                db.execute(text("INSERT INTO visits (%s) VALUES (%s)" % (", ".join(vv), ", ".join(vv.values()))),
                           {"cid": cid, "et": et, "xt": xt})
                vi += 1
                if random.random() < args.payments_every:
                    amt = round(random.choice([1500, 1900, 2400, 2900, 3400, 4200]) * random.uniform(0.9, 1.1), 2)
                    try:
                        db.execute(text("INSERT INTO payments (%s) VALUES (%s)" % (", ".join(p), ", ".join(p.values()))),
                                   {"cid": cid, "amt": amt, "et": et})
                        pi += 1
                    except Exception as e:
                        perr += 1
                        if perr <= 3:
                            print("PAY_WARN:", str(e)[:200], flush=True)
                db.commit()
            except Exception as e:
                db.rollback()
                print("VISIT_WARN:", str(e)[:200], flush=True)
        print("day %s: visits=%d payments=%d" % (day, vi, pi), flush=True)
    print("FILL_DONE visits=%d payments=%d pay_errors=%d" % (vi, pi, perr))

if __name__ == "__main__":
    main()
