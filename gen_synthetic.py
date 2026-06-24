import psycopg
from datetime import date, timedelta
import random

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

# Генерируем 60 дней истории
today = date.today()
metrics = ['attendance', 'revenue', 'new_clients', 'churn_risk']

for i in range(60, 0, -1):
    d = today - timedelta(days=i)
    
    # Attendance: 20-50 посещений, пик по выходным
    dow = d.weekday()
    base_attendance = 35 if dow < 5 else 50  # Больше в выходные
    attendance = base_attendance + random.randint(-10, 10)
    
    # Revenue: ~500-1500 ₽ за посещение
    revenue = attendance * random.randint(500, 1500)
    
    # New clients: 0-5
    new_clients = random.randint(0, 5)
    
    # Churn risk: 0-3
    churn_risk = random.randint(0, 3)
    
    for metric, value in [
        ('attendance', attendance),
        ('revenue', revenue),
        ('new_clients', new_clients),
        ('churn_risk', churn_risk),
    ]:
        cur.execute("""
            INSERT INTO analytics_daily (club_id, metric, date, value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value
        """, (1, metric, d, value))

conn.commit()
cur.close()
conn.close()

print(f"Inserted 60 days of synthetic data ({60 * 4} rows)")
