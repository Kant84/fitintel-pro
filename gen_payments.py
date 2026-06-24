import psycopg
from datetime import datetime, timezone, date, timedelta
import random
import uuid

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== Продолжаем: платежи ===")

# Получаем клиентов
cur.execute("SELECT id FROM clients LIMIT 10000")
client_ids = [row[0] for row in cur.fetchall()]
print(f"Клиентов: {len(client_ids)}")

# Генерируем платежи за 100 дней
total_payments = 0
for day_offset in range(100, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    daily_payments = random.randint(5, 15)
    for _ in range(daily_payments):
        client_id = random.choice(client_ids)
        amount = random.choice([1000, 2000, 3000, 5000, 7000, 10000])
        cur.execute("""
            INSERT INTO payments (id, client_id, amount, currency, payment_method, status, 
                                  payment_direction, payment_category, paid_at, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, 'RUB', 'CARD', 'completed', 
                    'INCOME', 'SUBSCRIPTION', %s, NOW(), NOW())
        """, (client_id, amount, datetime.combine(d, datetime.min.time()) + timedelta(hours=random.randint(8, 20))))
    total_payments += daily_payments
    if day_offset % 20 == 0:
        conn.commit()
        print(f"  День {day_offset}: {daily_payments} payments")

conn.commit()
print(f"Всего платежей: {total_payments}")

# Пересчитываем аналитику
print("Пересчёт аналитики...")
for day_offset in range(100, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    cur.execute("SELECT recalc_analytics_daily(1, %s)", (d,))
    if day_offset % 20 == 0:
        conn.commit()
        print(f"  Recalc day {day_offset}...")

conn.commit()
cur.close()
conn.close()

print("=== ГОТОВО! ===")
print(f"Всего посещений: 5858")
print(f"Всего платежей: {total_payments}")
print(f"Клиентов: 10000")
