# tools/demo/demo_stats_fill.py
"""Бэкфилл демо-статистики: визиты + платежи за последние N дней.

Даты считаются ОТ СЕГОДНЯ: перед каждым демо запускаете заново — статистика
Главной, тепловой карты и ML никогда не «проседает» ниже шкалы.

Работает ТОЛЬКО с фейковыми LT-клиентами (+7999LT%%) — реальным клиентам
ничего не отправляется. Пометка access_device_id/notes = 'DEMO_FILL' —
по ней чистится (--clean-first).

Запуск (внутри контейнера api):
    docker cp tools/demo/demo_stats_fill.py deploy-api-1:/tmp/fill.py
    docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T api \
        env PYTHONPATH=/app python /tmp/fill.py --days 60 --per-day 140 --clean-first

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
        vals = [r[0] for r in rows if r[0]]
        return random.choice(vals) if vals else fallback
    except Exception:
        return fallback

def has_col(db, table, col):
    r = db.execute(text("""SELECT 1 FROM information_schema.columns
        WHERE table_name=:t AND column_name=:c"""), {"t": table, "c": col}).first()
    return r is not None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--per-day", type=int, default=140)
    ap.add_argument("--payments-every", type=float, default=0.2, help="вероятность платежа на визит")
    ap.add_argument("--clean-first", action="store_true", help="удалить прошлую DEMO_FILL-статистику")
    args = ap.parse_args()

    db = SessionLocal()
    random.seed()
    today = datetime.now().date()
    now = datetime.now()

    if args.clean_first:
        r1 = db.execute(text("DELETE FROM visits WHERE access_device_id=:m"), {"m": MARK})
        if has_col(db, "payments", "notes"):
            r2 = db.execute(text("DELETE FROM payments WHERE notes=:m"), {"m": MARK})
        else:
            r2_row = db.execute(text("SELECT 0")).first()
            print("payments.notes отсутствует — старые DEMO-платежи не чистим")
        db.commit()
        print("CLEAN_DONE visits_deleted=%s" % (r1.rowcount or 0))

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
    pmethod = sample_col(db, "payments", "payment_method", "CARD")
    pstatus = sample_col(db, "payments", "status", "COMPLETED")

    v = defaults(db, "visits")
    v.update({"id": "gen_random_uuid()", "client_id": ":cid", "entry_time": ":et", "exit_time": ":xt",
              "status": "'%s'" % status, "access_granted": "true",
              "access_method": "'%s'" % method, "zone": "'GYM'",
              "access_device_id": "'%s'" % MARK, "created_at": ":et", "updated_at": ":xt"})
    if "notes" in v: v["notes"] = "'%s'" % MARK

    p = defaults(db, "payments")
    p.update({"id": "gen_random_uuid()", "client_id": ":cid", "amount": ":amt",
              "status": "'%s'" % pstatus, "payment_method": "'%s'" % pmethod, "created_at": ":et"})
    if "notes" in p: p["notes"] = "'%s'" % MARK

    vi = pi = 0
    for d in range(args.days, 0, -1):
        day = today - timedelta(days=d)
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
            if xt > now:           # сегодня ещё в клубе: без выхода, статус ACTIVE
                xt = None
                st = "ACTIVE"
            cid = random.choice(ids)
            try:
                vv = dict(v); vv["status"] = "'%s'" % st
                db.execute(text("INSERT INTO visits (%s) VALUES (%s)" % (", ".join(vv), ", ".join(vv.values()))),
                           {"cid": cid, "et": et, "xt": xt})
                vi += 1
                if random.random() < args.payments_every:
                    amt = round(random.choice([1500, 1900, 2400, 2900, 3400, 4200]) * random.uniform(0.9, 1.1), 2)
                    db.execute(text("INSERT INTO payments (%s) VALUES (%s)" % (", ".join(p), ", ".join(p.values()))),
                               {"cid": cid, "amt": amt, "et": et})
                    pi += 1
                db.commit()
            except Exception as e:
                db.rollback()
        print("day %s: visits=%d payments=%d" % (day, vi, pi), flush=True)
    print("FILL_DONE visits=%d payments=%d" % (vi, pi))

if __name__ == "__main__":
    main()
