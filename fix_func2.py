sql = """
CREATE OR REPLACE FUNCTION recalc_analytics_daily(p_club_id INT, p_date DATE)
RETURNS VOID AS ##DOLLAR##
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
##DOLLAR## LANGUAGE plpgsql;
""".replace("##DOLLAR##", chr(36)+chr(36))

import psycopg
conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()
cur.execute(sql)
conn.commit()
print("Function fixed v2!")
cur.close()
conn.close()
