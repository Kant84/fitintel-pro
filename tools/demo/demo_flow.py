# tools/demo/demo_flow.py
"""Живой поток клиентов во время демо: входы/выходы через VisitService.

Работает ТОЛЬКО с фейковыми LT-клиентами — обходится без HTTP/бонусов/MAX:
сервисный вызов, тихо и быстро. Подходит для показа «Входы/Выходы»,
«Кто в зале», тепловой карты в реальном времени.

Запуск (внутри контейнера api, в отдельном терминале/ssh):
    docker cp tools/demo/demo_flow.py deploy-api-1:/tmp/flow.py
    docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T api \
        env PYTHONPATH=/app python /tmp/flow.py --target 25 --interval 15 --min-stay 120 --max-stay 480

  --target     сколько клиентов держать «в клубе» одновременно
  --interval   секунд между попытками входа
  --min/max-stay  время «в клубе» в секундах (2-8 мин для демо)

Ctrl+C — выход; висящие визиты закроются штатно или через /visits/auto-close.
Маркер: каждые ~15 сек строка "В КЛУБЕ: N (входов: X, выходов: Y)".
"""
import argparse, random, time
from datetime import datetime
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.visit_service import VisitService

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=25)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--min-stay", type=int, default=120)
    ap.add_argument("--max-stay", type=int, default=480)
    args = ap.parse_args()

    db = SessionLocal()
    actor = db.execute(text("SELECT id FROM users WHERE is_superuser ORDER BY created_at LIMIT 1")).first()
    if not actor:
        print("Нет superuser-а в users"); return
    actor_id = str(actor[0])

    ids = [str(r[0]) for r in db.execute(text("""
        SELECT c.id FROM clients c
        WHERE c.is_active AND c.deleted_at IS NULL AND c.phone LIKE '+7999LT%%'
          AND EXISTS (SELECT 1 FROM subscriptions s WHERE s.client_id=c.id AND s.is_active)
        LIMIT 3000""")).all()]
    if not ids:
        print("Нет LT-клиентов! Сначала generate_data.py"); return

    svc = VisitService(db)
    in_club = []   # (visit_id, выход_в_эпохе)
    entries = exits = 0
    print("ПОТОК ЗАПУЩЕН: target=%d interval=%ds" % (args.target, args.interval), flush=True)
    try:
        while True:
            t0 = time.time()
            # выходы
            still = []
            for vid, leave_at in in_club:
                if time.time() >= leave_at:
                    try:
                        svc.exit(visit_id=vid, exit_time=datetime.now(), actor_user_id=actor_id)
                        exits += 1
                    except Exception as e:
                        print("exit warn:", str(e)[:120], flush=True)
                else:
                    still.append((vid, leave_at))
            in_club = still
            # входы
            if len(in_club) < args.target and random.random() < 0.9:
                cid = random.choice(ids)
                try:
                    v = svc.entry(client_id=cid, access_method="RFID",
                                  access_device_id="DEMO_FLOW", zone="GYM",
                                  entry_time=datetime.now(), actor_user_id=actor_id)
                    in_club.append((str(v.id), time.time() + random.randint(args.min_stay, args.max_stay)))
                    entries += 1
                except Exception as e:
                    msg = str(e)
                    if "уже" not in msg.lower() and "already" not in msg.lower():
                        print("entry warn:", msg[:120], flush=True)
            print("В КЛУБЕ: %d (входов: %d, выходов: %d)" % (len(in_club), entries, exits), flush=True)
            time.sleep(max(1, args.interval - (time.time() - t0)))
    except KeyboardInterrupt:
        print("Остановлено. В клубе осталось: %d — закройте через POST /visits/auto-close" % len(in_club))

if __name__ == "__main__":
    main()
