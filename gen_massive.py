import psycopg
from datetime import datetime, timezone, date, timedelta
import random
import uuid

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== Генерация масштабных данных ===")
print("100 дней, 10000 клиентов, посещения, платежи...")

# 1. Генерируем 10000 клиентов
print("1. Создаём 10000 клиентов...")
for i in range(10000):
    client_id = str(uuid.uuid4())
    first_name = f"Client{i}"
    last_name = f"Test{i}"
    phone = f"+7900000{i:05d}"
    email = f"client{i}@test.com"
    cur.execute("""
        INSERT INTO clients (id, first_name, last_name, phone, email, gender, client_category, status, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, 'МУЖСКОЙ', 'ОБЫЧНАЯ', 'ACTIVE', true, NOW() - INTERVAL '%s days', NOW() - INTERVAL '%s days')
        ON CONFLICT (phone) DO NOTHING
    """, (client_id, first_name, last_name, phone, email, random.randint(0, 100), random.randint(0, 100)))
    if i % 1000 == 0:
        conn.commit()
        print(f"  {i} клиентов...")

conn.commit()
print("Клиенты созданы!")

# 2. Получаем ID клиентов
cur.execute("SELECT id FROM clients LIMIT 10000")
client_ids = [row[0] for row in cur.fetchall()]
print(f"Получено {len(client_ids)} клиентов")

# 3. Генерируем посещения за 100 дней
print("2. Создаём посещения...")
total_visits = 0
for day_offset in range(100, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    # 30-80 посещений в день
    daily_visits = random.randint(30, 80)
    for _ in range(daily_visits):
        client_id = random.choice(client_ids)
        entry_time = datetime.combine(d, datetime.min.time()) + timedelta(hours=random.randint(6, 22), minutes=random.randint(0, 59))
        duration = random.randint(30, 180)
        exit_time = entry_time + timedelta(minutes=duration)
        cur.execute("""
            INSERT INTO visits (id, client_id, entry_time, exit_time, status, duration_minutes, zone, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, %s, 'COMPLETED', %s, 'GYM', NOW(), NOW())
        """, (client_id, entry_time, exit_time, duration))
    total_visits += daily_visits
    if day_offset % 10 == 0:
        conn.commit()
        print(f"  День {day_offset}: {daily_visits} visits, total={total_visits}")

conn.commit()
print(f"Всего посещений: {total_visits}")

# 4. Генерируем платежи
print("3. Создаём платежи...")
total_payments = 0
for day_offset in range(100, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    # 5-15 платежей в день
    daily_payments = random.randint(5, 15)
    for _ in range(daily_payments):
        client_id = random.choice(client_ids)
        amount = random.choice([1000, 2000, 3000, 5000, 7000, 10000])
        cur.execute("""
            INSERT INTO payments (id, client_id, amount, status, payment_method, description, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, 'completed', 'CARD', 'Абонемент', %s, NOW())
        """, (client_id, amount, datetime.combine(d, datetime.min.time()) + timedelta(hours=random.randint(8, 20))))
    total_payments += daily_payments
    if day_offset % 20 == 0:
        conn.commit()
        print(f"  День {day_offset}: {daily_payments} payments")

conn.commit()
print(f"Всего платежей: {total_payments}")

# 5. Пересчитываем аналитику за все 100 дней
print("4. Пересчёт аналитики за 100 дней...")
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
print(f"Клиентов: 10000")
print(f"Посещений: {total_visits}")
print(f"Платежей: {total_payments}")
print(f"Аналитика: 100 дней пересчитана")
