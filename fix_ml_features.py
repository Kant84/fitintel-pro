import psycopg

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

# Удаляем старую функцию
cur.execute("DROP FUNCTION IF EXISTS get_ml_features(INT, DATE)")

# Создаём исправленную
func_sql = """
CREATE OR REPLACE FUNCTION get_ml_features(p_club_id INT, p_date DATE)
RETURNS TABLE (
    metric_date DATE, club_id INT, visits_count INT, revenue_total NUMERIC,
    new_contracts INT, day_of_week INT, month INT, day_of_month INT,
    is_weekend INT, is_holiday INT, is_pre_holiday INT, is_payday INT,
    campaign_active INT, season VARCHAR,
    visits_lag_1 INT, visits_lag_7 INT, visits_lag_14 INT, visits_lag_30 INT,
    visits_rolling_7 NUMERIC, visits_rolling_14 NUMERIC,
    revenue_rolling_7 NUMERIC, revenue_rolling_14 NUMERIC,
    visits_trend NUMERIC
) AS __DOLLAR__
BEGIN
    RETURN QUERY
    WITH metrics AS (
        SELECT 
            m.date as d, m.club_id as cid, m.visits_count, m.revenue_total,
            m.new_contracts_count,
            EXTRACT(ISODOW FROM m.date)::int as dow,
            EXTRACT(MONTH FROM m.date)::int as mon,
            EXTRACT(DAY FROM m.date)::int as dom,
            CASE WHEN EXTRACT(ISODOW FROM m.date) IN (6, 7) THEN 1 ELSE 0 END as weekend,
            f.is_holiday, f.is_pre_holiday, f.is_payday, f.campaign_active, f.season
        FROM club_daily_metrics m
        LEFT JOIN analytics_factors f ON f.date = m.date
        WHERE m.club_id = p_club_id
          AND m.date <= p_date
          AND m.date >= p_date - INTERVAL '60 days'
    ),
    lags AS (
        SELECT 
            m.d, m.cid, m.visits_count, m.revenue_total, m.new_contracts_count,
            m.dow, m.mon, m.dom, m.weekend,
            CASE WHEN m.is_holiday THEN 1 ELSE 0 END as is_holiday_int,
            CASE WHEN m.is_pre_holiday THEN 1 ELSE 0 END as is_pre_holiday_int,
            CASE WHEN m.is_payday THEN 1 ELSE 0 END as is_payday_int,
            CASE WHEN m.campaign_active THEN 1 ELSE 0 END as campaign_int,
            m.season,
            LAG(m.visits_count, 1) OVER (ORDER BY m.d) as lag_1,
            LAG(m.visits_count, 7) OVER (ORDER BY m.d) as lag_7,
            LAG(m.visits_count, 14) OVER (ORDER BY m.d) as lag_14,
            LAG(m.visits_count, 30) OVER (ORDER BY m.d) as lag_30,
            AVG(m.visits_count) OVER (ORDER BY m.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as roll_7,
            AVG(m.visits_count) OVER (ORDER BY m.d ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as roll_14,
            AVG(m.revenue_total) OVER (ORDER BY m.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rev_roll_7,
            AVG(m.revenue_total) OVER (ORDER BY m.d ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) as rev_roll_14,
            (m.visits_count - LAG(m.visits_count, 7) OVER (ORDER BY m.d))::NUMERIC as trend
        FROM metrics m
    )
    SELECT * FROM lags WHERE d = p_date;
END;
__DOLLAR__ LANGUAGE plpgsql;
""".replace('__DOLLAR__', chr(36)+chr(36))

cur.execute(func_sql)
conn.commit()

# Тест
cur.execute("SELECT * FROM get_ml_features(1, CURRENT_DATE)")
row = cur.fetchone()
if row:
    print(f"Фичи: visits={row[2]}, lag_1={row[14]}, lag_7={row[15]}, rolling_7={row[18]:.1f}, trend={row[22]:.1f}")
else:
    print("Нет данных (нужно минимум 30 дней истории)")

cur.close()
conn.close()
print("=== Готово! ===")
