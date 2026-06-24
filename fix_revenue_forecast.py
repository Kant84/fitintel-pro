# fix_revenue_forecast.py
with open('app/services/analytics_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # Извлекаем фичи
        visits = result.visits_count or 0
        lag_1 = result.visits_lag_1 or 0
        lag_7 = result.visits_lag_7 or 0
        rolling_7 = float(result.visits_rolling_7) if result.visits_rolling_7 else 0
        rolling_14 = float(result.visits_rolling_14) if result.visits_rolling_14 else 0
        trend = float(result.visits_trend) if result.visits_trend else 0
        is_weekend = result.is_weekend or 0
        is_payday = result.is_payday or 0
        season = result.season or 'neutral'
        
        # Мультифакторная модель (взвешенная сумма)
        # База: rolling_7 (среднее за неделю)
        base = rolling_7'''

new = '''        # Извлекаем фичи в зависимости от метрики
        visits = result.visits_count or 0
        lag_1 = result.visits_lag_1 or 0
        lag_7 = result.visits_lag_7 or 0
        
        # Для revenue используем revenue_rolling, для attendance — visits_rolling
        if metric == 'revenue':
            rolling_7 = float(result.revenue_rolling_7) if result.revenue_rolling_7 else 0
            rolling_14 = float(result.revenue_rolling_14) if result.revenue_rolling_14 else 0
        else:
            rolling_7 = float(result.visits_rolling_7) if result.visits_rolling_7 else 0
            rolling_14 = float(result.visits_rolling_14) if result.visits_rolling_14 else 0
            
        trend = float(result.visits_trend) if result.visits_trend else 0
        is_weekend = result.is_weekend or 0
        is_payday = result.is_payday or 0
        season = result.season or 'neutral'
        
        # Мультифакторная модель (взвешенная сумма)
        # База: rolling_7 (среднее за неделю)
        base = rolling_7'''

if old in content:
    content = content.replace(old, new)
    with open('app/services/analytics_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Revenue forecast fixed!")
else:
    print("ERROR: Pattern not found")
