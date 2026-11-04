"""Генератор данных для нагрузочного теста FitIntel Pro.
Запуск внутри контейнера api:
    docker cp tools/loadtest/generate_data.py deploy-api-1:/tmp/gen.py
    docker compose ... exec -T api env PYTHONPATH=/app python /tmp/gen.py --clients 20000
Клиенты помечаются телефоном +7999LTxxxxxx - легко найти и удалить:
    DELETE FROM clients WHERE phone LIKE '+7999LT%';
"""
import argparse, random
from sqlalchemy import text
from app.db.session import SessionLocal

FIRST = ["Александр","Дмитрий","Максим","Сергей","Андрей","Алексей","Артём","Илья","Кирилл","Михаил",
         "Елена","Ольга","Наталья","Екатерина","Мария","Анна","Татьяна","Ирина","Юлия","Светлана"]
LAST = ["Иванов","Смирнов","Кузнецов","Попов","Васильев","Петров","Соколов","Михайлов","Новиков","Федоров",
        "Морозова","Волкова","Алексеева","Лебедева","Семенова","Егорова","Павлова","Козлова","Степанова","Николаева"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=1000)
    args = ap.parse_args()
    db = SessionLocal()
    g = db.execute(text("SELECT gender FROM clients WHERE gender IS NOT NULL LIMIT 1")).first()
    gender = g[0] if g else "M"
    total = 0
    for start in range(0, args.clients, args.batch):
        n = min(args.batch, args.clients - start)
        rows = [{"first": random.choice(FIRST), "last": random.choice(LAST), "gender": gender,
                 "phone": "+7999LT%06d" % (start + i),
                 "email": "lt%06d@load.test" % (start + i)} for i in range(n)]
        db.execute(text("INSERT INTO clients (first_name, last_name, gender, phone, email, created_at) "
                        "VALUES (:first, :last, :gender, :phone, :email, now())"), rows)
        db.commit()
        total += n
        print("clients: %d" % total, flush=True)
    print("GENERATE_DONE=%d" % total)

if __name__ == "__main__":
    main()
