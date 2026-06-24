import psycopg
from datetime import datetime, date, timedelta
import random
import uuid

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== Дополнение данных ===")

# Получаем клиентов
cur.execute("SELECT id FROM clients LIMIT 10000")
client_ids = [row[0] for row in cur.fetchall()]

# Дополняем посещения: +10000, с реалистичными паттернами
print("1. Дополнительные 10000 посещений...")
for i in range(10000):
    # Реалистичные паттерны
    d = date.today() - timedelta(days=random.randint(1, 100))
    dow = d.weekday()
    
    # Пик в 18:00-21:00 в будни, 10:00-14:00 в выходные
    if dow < 5:  # Будни
        hour = random.choice([7,8,9,17,18,19,20,21])
    else:  # Выходные
        hour = random.choice([9,10,11,12,13,14,15,16,17])
    
    entry_time = datetime.combine(d, datetime.min.time()) + timedelta(hours=hour, minutes=random.randint(0, 59))
    duration = random.randint(45, 150)  # 45 мин - 2.5 часа
    exit_time = entry_time + timedelta(minutes=duration)
    
    # Зоны: GYM (60%), POOL (20%), SPA (10%), GROUP (10%)
    zone = random.choices(['GYM', 'POOL', 'SPA', 'GROUP'], weights=[60, 20, 10, 10])[0]
    
    client_id = random.choice(client_ids)
    cur.execute("""
        INSERT INTO visits (id, client_id, entry_time, exit_time, status, duration_minutes, zone, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, %s, 'COMPLETED', %s, %s, NOW(), NOW())
    """, (client_id, entry_time, exit_time, duration, zone))

conn.commit()
print("Посещения дополнены!")

# Дополняем платежи: +2000, разные суммы
print("2. Дополнительные 2000 платежей...")
for i in range(2000):
    d = date.today() - timedelta(days=random.randint(1, 100))
    client_id = random.choice(client_ids)
    # Разные типы абонементов
    amount = random.choices([1500, 3000, 5000, 8000, 12000, 20000], weights=[10, 25, 30, 20, 10, 5])[0]
    method = random.choices(['CARD', 'CASH', 'SBP', 'ONLINE'], weights=[50, 20, 20, 10])[0]
    
    cur.execute("""
        INSERT INTO payments (id, client_id, amount, currency, payment_method, status, 
                              payment_direction, payment_category, paid_at, created_at, updated_at)
        VALUES (gen_random_uuid(), %s, %s, 'RUB', %s, 'completed', 
                'INCOME', 'SUBSCRIPTION', %s, NOW(), NOW())
    """, (client_id, amount, method, datetime.combine(d, datetime.min.time()) + timedelta(hours=random.randint(8, 20))))

conn.commit()
print("Платежи дополнены!")

# Пересчёт аналитики
print("3. Пересчёт аналитики...")
for day_offset in range(100, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    cur.execute("SELECT recalc_analytics_daily(1, %s)", (d,))
    if day_offset % 20 == 0:
        conn.commit()
        print(f"  Day {day_offset}...")

conn.commit()
cur.close()
conn.close()

print("=== ГОТОВО! ===")
print("Теперь данные плотные и реалистичные!")
