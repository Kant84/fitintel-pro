"""Генератор данных для нагрузочного теста FitIntel Pro (v3 - авто-заполнение NOT NULL).
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

def default_expr(name, dtype):
    d = (dtype or "").lower()
    if "timestamp" in d or d == "date":
        return "now()"
    if d in ("integer", "bigint", "smallint", "numeric", "real", "double precision"):
        return "0"
    if d == "boolean":
        return "false"
    if "uuid" in d:
        return "gen_random_uuid()"
    return "'LOAD'"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=1000)
    args = ap.parse_args()
    db = SessionLocal()

    # NOT NULL колонки без DEFAULT (id/created_at исключаем - у них значения)
    cols = db.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'clients' AND is_nullable = 'NO'
          AND column_default IS NULL
          AND column_name NOT IN ('id', 'created_at')
        ORDER BY ordinal_position""")).all()

    # реальные значения-образцы из базы (не гадаем соглашения)
    def sample(col):
        r = db.execute(text("SELECT %s FROM clients WHERE %s IS NOT NULL LIMIT 1" % (col, col))).first()
        return r[0] if r else None
    gender_val = sample("gender") or "НЕ_УКАЗАН"
    cat_val = sample("client_category") or "Обычный"

    values = {"first_name": ":first", "last_name": ":last", "phone": ":phone",
              "email": ":email", "created_at": "now()",
              "gender": ":gender", "client_category": ":cat"}
    for name, dtype in cols:
        if name not in values:
            values[name] = default_expr(name, dtype)

    uk = db.execute(text("""
        SELECT 1 FROM pg_indexes WHERE tablename = 'clients'
          AND indexdef ILIKE '%%UNIQUE%%' AND indexdef ILIKE '%%(phone)%%'""")).first()
    conflict = "ON CONFLICT (phone) DO NOTHING" if uk else ""

    sql = "INSERT INTO clients (%s) VALUES (%s) %s" % (
        ", ".join(values.keys()), ", ".join(values.values()), conflict)

    total = 0
    for start in range(0, args.clients, args.batch):
        n = min(args.batch, args.clients - start)
        rows = [{"first": random.choice(FIRST), "last": random.choice(LAST),
                 "gender": gender_val, "cat": cat_val,
                 "phone": "+7999LT%06d" % (start + i),
                 "email": "lt%06d@load.test" % (start + i)} for i in range(n)]
        db.execute(text(sql), rows)
        db.commit()
        total += n
        print("clients: %d" % total, flush=True)
    print("GENERATE_DONE=%d" % total)

if __name__ == "__main__":
    main()
