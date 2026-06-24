import psycopg
from datetime import date
import random

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

today = date.today()
cur.execute("""
    INSERT INTO analytics_daily (club_id, metric, date, value)
    VALUES 
        (2, 'attendance', %s, 15),
        (2, 'revenue', %s, 3500),
        (2, 'new_clients', %s, 1),
        (2, 'churn_risk', %s, 0)
    ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value
""", (today, today, today, today))

conn.commit()
cur.close()
conn.close()

print("Данные за сегодня для club_id=2 добавлены!")
