# tests/manual/create_old_sale.py
import psycopg
from datetime import datetime, timedelta

conn = psycopg.connect("postgresql://postgres:FitNexus_Postgres_2026!@127.0.0.1:5432/fitnexus")
cur = conn.cursor()

# Создаём продажу старше 24 часов
old_time = datetime.now() - timedelta(hours=25)
cur.execute("""
    INSERT INTO sales (id, cashier_id, total_amount, payment_method, items, status, created_at)
    VALUES (
        '22222222-2222-2222-2222-222222222222',
        '7db07a4c-0bf9-4a57-bd9f-9f088ba15783',
        100.00,
        'CASH',
        '[{"product_id": "11111111-1111-1111-1111-111111111111", "quantity": 1, "price": "100.0"}]'::jsonb,
        'COMPLETED',
        %s
    )
    ON CONFLICT (id) DO NOTHING
""", (old_time,))

conn.commit()
cur.close()
conn.close()
print("Old sale created!")
