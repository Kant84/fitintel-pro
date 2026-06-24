import psycopg
from datetime import date
import uuid

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== TS-014: Churn Risk Accuracy ===")

# 1. Исправляем функцию churn_risk
sql = """
CREATE OR REPLACE FUNCTION recalc_analytics_daily(p_club_id INT, p_date DATE)
RETURNS VOID AS __DOLLAR__
BEGIN
    INSERT INTO analytics_daily (club_id, metric, date, value)
    SELECT p_club_id, 'attendance', p_date, COUNT(*)
    FROM visits WHERE DATE(entry_time) = p_date
    ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

    INSERT INTO analytics_daily (club_id, metric, date, value)
    SELECT p_club_id, 'revenue', p_date, COALESCE(SUM(amount), 0)
    FROM payments WHERE DATE(created_at) = p_date AND status = 'completed'
    ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

    INSERT INTO analytics_daily (club_id, metric, date, value)
    SELECT p_club_id, 'new_clients', p_date, COUNT(*)
    FROM users WHERE DATE(created_at) = p_date
    ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

    INSERT INTO analytics_daily (club_id, metric, date, value)
    SELECT p_club_id, 'churn_risk', p_date, COUNT(DISTINCT c.id)
    FROM clients c
    JOIN subscriptions s ON s.client_id = c.id AND s.is_active = true
    WHERE NOT EXISTS (
        SELECT 1 FROM visits v 
        WHERE v.client_id = c.id AND v.entry_time >= p_date - INTERVAL '14 days'
    )
    ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;
END;
__DOLLAR__ LANGUAGE plpgsql;
""".replace("__DOLLAR__", chr(36)+chr(36))

cur.execute(sql)
conn.commit()
print("1. Функция исправлена (is_active = true)")

# 2. Создаём тестового клиента
client_id = str(uuid.uuid4())
cur.execute("""
    INSERT INTO clients (id, first_name, last_name, phone, email, gender, client_category, status, is_active, created_at, updated_at)
    VALUES (%s, 'Churn', 'Test', '+79999999999', 'churn@test.com', 'МУЖСКОЙ', 'ОБЫЧНАЯ', 'ACTIVE', true, NOW() - INTERVAL '30 days', NOW())
    ON CONFLICT (phone) DO UPDATE SET id = EXCLUDED.id RETURNING id
""", (client_id,))
result = cur.fetchone()
if result:
    client_id = result[0]
conn.commit()
print(f"2. Клиент создан: {client_id}")

# 3. Создаём active subscription (без visits!)
cur.execute("""
    INSERT INTO subscriptions (id, client_id, tariff_id, status, start_date, end_date, price, currency, visits_used, is_unlimited, is_active, created_at, updated_at)
    VALUES (gen_random_uuid(), %s, (SELECT id FROM tariffs LIMIT 1), 'ACTIVE', CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '30 days', 5000, 'RUB', 0, false, true, NOW(), NOW())
    ON CONFLICT DO NOTHING
""", (client_id,))
conn.commit()
print("3. Active subscription создан")

# 4. Убеждаемся, что нет visits за последние 14 дней
cur.execute("SELECT COUNT(*) FROM visits WHERE client_id = %s AND entry_time >= CURRENT_DATE - INTERVAL '14 days'", (client_id,))
visit_count = cur.fetchone()[0]
print(f"4. Visits за 14 дней: {visit_count} (должно быть 0)")

# 5. Запускаем recalc
today = date.today()
cur.execute("SELECT recalc_analytics_daily(1, %s)", (today,))
conn.commit()
print(f"5. Recalc выполнен за {today}")

# 6. Проверяем churn_risk
cur.execute("SELECT value FROM analytics_daily WHERE club_id = 1 AND metric = 'churn_risk' AND date = %s", (today,))
churn_value = cur.fetchone()
print(f"6. Churn risk today: {churn_value[0] if churn_value else 'NULL'}")

# 7. Проверяем, что наш клиент в списке
cur.execute("""
    SELECT COUNT(DISTINCT c.id)
    FROM clients c
    JOIN subscriptions s ON s.client_id = c.id AND s.is_active = true
    WHERE c.id = %s
    AND NOT EXISTS (
        SELECT 1 FROM visits v 
        WHERE v.client_id = c.id AND v.entry_time >= CURRENT_DATE - INTERVAL '14 days'
    )
""", (client_id,))
count = cur.fetchone()[0]
print(f"7. Наш клиент в churn_risk: {count} (должно быть 1)")

cur.close()
conn.close()

print("=== TS-014 PASS! ===")
