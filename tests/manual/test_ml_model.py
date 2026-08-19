import psycopg
from datetime import date, timedelta
import random

conn = psycopg.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='FitNexus_Postgres_2026!')
cur = conn.cursor()

print("=== Тестирование ML-модели на сгенерированных данных ===")

# 1. Очищаем тестовые данные за последние 30 дней для club_id=1
cur.execute("DELETE FROM club_daily_metrics WHERE club_id = 1 AND date >= CURRENT_DATE - INTERVAL '30 days'")
cur.execute("DELETE FROM analytics_factors WHERE date >= CURRENT_DATE - INTERVAL '30 days'")
conn.commit()

# 2. Генерируем реалистичные данные за 30 дней
print("1. Генерация реалистичных данных (30 дней)...")

base_visits = 120  # Базовое количество посещений

for day_offset in range(30, 0, -1):
    d = date.today() - timedelta(days=day_offset)
    dow = d.weekday()  # 0=Пн, 6=Вс
    dom = d.day
    
    # Факторы
    is_weekend = dow >= 5
    is_payday = dom in [5, 6, 7, 8, 9, 10, 15, 16, 17, 18, 19, 20]
    season = 'summer' if d.month in [6, 7, 8] else 'winter'
    
    # Реалистичная формула посещений
    # База + день недели + зарплата + сезон + случайный шум + тренд
    visits = base_visits
    
    # Выходные: +30%
    if is_weekend:
        visits = int(visits * 1.3)
    else:
        # Будни: пик в среду, спад в понедельник
        dow_mult = {0: 0.85, 1: 0.95, 2: 1.0, 3: 1.1, 4: 1.05, 5: 1.3, 6: 1.25}
        visits = int(visits * dow_mult[dow])
    
    # Зарплатные дни: +15%
    if is_payday:
        visits = int(visits * 1.15)
    
    # Сезон (лето: -10%)
    if season == 'summer':
        visits = int(visits * 0.9)
    
    # Тренд: растём на 2% в неделю
    week_num = (30 - day_offset) // 7
    visits = int(visits * (1 + week_num * 0.02))
    
    # Случайный шум ±10%
    visits = int(visits * random.uniform(0.9, 1.1))
    
    # Revenue = visits * 150 (средний чек)
    revenue = visits * 150
    
    # Новые контракты = 5% от посещений
    new_contracts = max(1, int(visits * 0.05))
    
    # Записываем
    cur.execute("""
        INSERT INTO club_daily_metrics (date, club_id, visits_count, revenue_total, new_contracts_count)
        VALUES (%s, 1, %s, %s, %s)
        ON CONFLICT (date, club_id) DO UPDATE SET
            visits_count = EXCLUDED.visits_count,
            revenue_total = EXCLUDED.revenue_total,
            new_contracts_count = EXCLUDED.new_contracts_count
    """, (d, visits, revenue, new_contracts))
    
    # Факторы
    cur.execute("""
        INSERT INTO analytics_factors (date, is_payday, season, is_holiday, is_pre_holiday, campaign_active)
        VALUES (%s, %s, %s, false, false, false)
        ON CONFLICT (date) DO UPDATE SET
            is_payday = EXCLUDED.is_payday,
            season = EXCLUDED.season
    """, (d, is_payday, season))

conn.commit()
print(f"   Данные за 30 дней созданы (base={base_visits})")

# 3. Проверяем данные
print("\n2. Проверка сгенерированных данных:")
cur.execute("""
    SELECT date, visits_count, revenue_total, 
           EXTRACT(ISODOW FROM date)::int as dow
    FROM club_daily_metrics 
    WHERE club_id = 1 AND date >= CURRENT_DATE - INTERVAL '14 days'
    ORDER BY date DESC
    LIMIT 7
""")
rows = cur.fetchall()
for row in rows:
    dow_name = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][row[3]-1]
    print(f"   {row[0]} ({dow_name}): visits={row[1]}, revenue={row[2]:,.0f} ₽")

# 4. Проверяем ML-фичи
print("\n3. ML-фичи для сегодня:")
cur.execute("SELECT * FROM get_ml_features(1, CURRENT_DATE)")
row = cur.fetchone()
if row:
    print(f"   visits_count: {row[2]}")
    print(f"   lag_1 (вчера): {row[14]}")
    print(f"   lag_7 (неделю назад): {row[15]}")
    print(f"   lag_14 (2 недели назад): {row[16]}")
    print(f"   rolling_7 (средняя 7 дней): {row[18]:.1f}")
    print(f"   rolling_14 (средняя 14 дней): {row[19]:.1f}")
    print(f"   trend (тренд): {row[22]:.1f}")
    print(f"   season: {row[13]}")
    print(f"   is_payday: {row[11]}")
    print(f"   is_weekend: {row[9]}")

# 5. Тестируем прогноз через API
print("\n4. Тест прогноза через API...")
cur.close()
conn.close()

print("\n=== Данные готовы для теста! ===")
print("Запусти сервер и проверь:")
print("  POST /api/v1/analytics/forecast?club_id=1")
print("  Body: { 'metric': 'attendance', 'days_ahead': 7 }")
