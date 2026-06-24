# fix_analytics_service_ml.py
with open('app/services/analytics_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_forecast = '''    def forecast(self, club_id: int, metric: str, days_ahead: int = 7) -> dict:
        """Прогноз на N дней (E16)"""
        # Получаем 56 дней истории
        end_date = date.today()
        start_date = end_date - timedelta(days=56)
        
        history = (
            self.db.query(AnalyticsDaily)
            .filter(
                AnalyticsDaily.club_id == club_id,
                AnalyticsDaily.metric == metric,
                AnalyticsDaily.date >= start_date,
                AnalyticsDaily.date <= end_date,
            )
            .order_by(AnalyticsDaily.date)
            .all()
        )
        
        if len(history) < 14:
            return {
                "metric": metric,
                "history": [],
                "forecast": [],
                "trend": "UNKNOWN",
                "recommendation": "Недостаточно данных для прогноза (минимум 14 дней)",
            }
        
        # Группировка по DOW (0=Пн, 6=Вс)
        dow_values = {i: [] for i in range(7)}
        for h in history:
            dow = h.date.weekday()  # 0=Пн
            dow_values[dow].append(float(h.value))
        
        # Среднее по DOW
        dow_avg = {}
        for dow, values in dow_values.items():
            dow_avg[dow] = sum(values) / len(values) if values else 0
        
        # Тренд (последние 7 дней vs предыдущие 7)
        last_7 = [float(h.value) for h in history[-7:]]
        prev_7 = [float(h.value) for h in history[-14:-7]]
        trend_val = (sum(last_7) / len(last_7)) - (sum(prev_7) / len(prev_7)) if prev_7 else 0
        
        # Прогноз
        forecast_points = []
        for i in range(1, days_ahead + 1):
            forecast_date = end_date + timedelta(days=i)
            dow = forecast_date.weekday()
            base = dow_avg.get(dow, 0)
            trend_adj = trend_val * (i / 7)
            value = max(0, base + trend_adj)
            forecast_points.append({
                "date": forecast_date,
                "value": round(value, 2),
                "is_forecast": True,
            })
        
        # Trend
        if trend_val > base * 0.05:
            trend = "UP"
            recommendation = "Положительный тренд. Рассмотрите расширение услуг."
        elif trend_val < -base * 0.05:
            trend = "DOWN"
            recommendation = "Отрицательный тренд. Запустите акцию или проверьте удержание."
        else:
            trend = "STABLE"
            recommendation = "Стабильность. Поддерживайте текущие процессы."
        
        # History points
        history_points = [
            {"date": h.date, "value": float(h.value), "is_forecast": False}
            for h in history[-14:]  # Последние 14 дней для графика
        ]
        
        return {
            "metric": metric,
            "history": history_points,
            "forecast": forecast_points,
            "trend": trend,
            "recommendation": recommendation,
        }'''

new_forecast = '''    def forecast(self, club_id: int, metric: str, days_ahead: int = 7) -> dict:
        """Мультифакторный прогноз на N дней (ML-фичи: лаги, rolling, сезонность, факторы)"""
        from sqlalchemy import text
        from datetime import date, timedelta
        
        end_date = date.today()
        
        # Получаем ML-фичи из SQL
        result = self.db.execute(
            text("SELECT * FROM get_ml_features(:club_id, :date)"),
            {"club_id": club_id, "date": end_date}
        ).fetchone()
        
        if not result:
            return {
                "metric": metric,
                "history": [],
                "forecast": [],
                "trend": "UNKNOWN",
                "recommendation": "Недостаточно данных для прогноза",
            }
        
        # Извлекаем фичи
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
        base = rolling_7
        
        # Тренд: учитываем направление
        trend_weight = 0.3
        trend_adj = trend * trend_weight
        
        # Сезонность: корректировка по времени года
        season_mult = {
            'winter': 0.9,   # зима = меньше посещений
            'spring': 1.0,   # весна = норма
            'summer': 0.85,  # лето = отпуска
            'autumn': 1.1    # осень = больше (после отпусков)
        }.get(season, 1.0)
        
        # Зарплата: в дни зарплаты больше платежей
        payday_boost = 1.15 if is_payday else 1.0
        
        # Выходные: больше посещений
        weekend_boost = 1.2 if is_weekend else 1.0
        
        # Итоговый прогноз
        forecast_value = max(0, (base + trend_adj) * season_mult * payday_boost * weekend_boost)
        
        # Тренд для UI
        if trend > rolling_7 * 0.05:
            trend_str = "UP"
            recommendation = "Положительный тренд. Спрос растёт, рассмотрите расширение."
        elif trend < -rolling_7 * 0.05:
            trend_str = "DOWN"
            recommendation = "Отрицательный тренд. Запустите акцию или проверьте удержание."
        else:
            trend_str = "STABLE"
            recommendation = "Стабильность. Поддерживайте текущие процессы."
        
        # Прогноз на N дней
        forecast_points = []
        for i in range(1, days_ahead + 1):
            forecast_date = end_date + timedelta(days=i)
            # Для каждого дня вперед используем свою логику
            dow = forecast_date.weekday()
            is_wd = 1 if dow >= 5 else 0  # 5=Сб, 6=Вс
            day_value = max(0, forecast_value * (1.0 if not is_wd else 1.2))
            forecast_points.append({
                "date": forecast_date,
                "value": round(day_value, 2),
                "is_forecast": True,
            })
        
        # История (последние 14 дней)
        history = (
            self.db.query(AnalyticsDaily)
            .filter(
                AnalyticsDaily.club_id == club_id,
                AnalyticsDaily.metric == metric,
                AnalyticsDaily.date >= end_date - timedelta(days=14),
            )
            .order_by(AnalyticsDaily.date)
            .all()
        )
        history_points = [
            {"date": h.date, "value": float(h.value), "is_forecast": False}
            for h in history
        ]
        
        return {
            "metric": metric,
            "history": history_points,
            "forecast": forecast_points,
            "trend": trend_str,
            "recommendation": recommendation,
            "ml_features": {
                "base": round(base, 2),
                "trend": round(trend, 2),
                "season": season,
                "season_mult": season_mult,
                "payday_boost": payday_boost,
                "weekend_boost": weekend_boost,
                "lag_7": lag_7,
                "rolling_7": round(rolling_7, 2),
            }
        }'''

if old_forecast in content:
    content = content.replace(old_forecast, new_forecast)
    with open('app/services/analytics_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("AnalyticsService обновлён с ML-фичами!")
else:
    print("ERROR: Не найден старый forecast")
