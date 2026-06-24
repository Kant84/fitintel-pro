import psycopg
from datetime import date, timedelta
import random

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== TS-013: Многоклубная изоляция ===")

# 1. Создаём данные для club_id=2 (другие значения)
today = date.today()
for day_offset in range(30, 0, -1):
    d = today - timedelta(days=day_offset)
    cur.execute("""
        INSERT INTO analytics_daily (club_id, metric, date, value)
        VALUES 
            (2, 'attendance', %s, %s),
            (2, 'revenue', %s, %s),
            (2, 'new_clients', %s, %s),
            (2, 'churn_risk', %s, %s)
        ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value
    """, (d, random.randint(5, 20), d, random.randint(1000, 5000), d, random.randint(0, 2), d, random.randint(0, 1)))

conn.commit()
print("1. Данные для club_id=2 созданы")

# 2. Проверяем club_id=1
cur.execute("SELECT metric, SUM(value) FROM analytics_daily WHERE club_id = 1 AND date = %s GROUP BY metric", (today,))
club1_data = cur.fetchall()
print(f"2. Club 1 today: {club1_data}")

# 3. Проверяем club_id=2
cur.execute("SELECT metric, SUM(value) FROM analytics_daily WHERE club_id = 2 AND date = %s GROUP BY metric", (today,))
club2_data = cur.fetchall()
print(f"3. Club 2 today: {club2_data}")

# 4. Проверяем через API
cur.close()
conn.close()

print("=== Данные готовы для теста ===")
print("Теперь проверим API:")
print("  GET /api/v1/analytics/dashboard?club_id=1 → только данные club 1")
print("  GET /api/v1/analytics/dashboard?club_id=2 → только данные club 2")
