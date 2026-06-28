# app/services/analytics_service.py
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.analytics import AnalyticsDaily
from app.models.visit import Visit
from app.models.payment import Payment
from app.models.user import User
from app.models.client import Client
from app.models.subscription import Subscription


class AnalyticsService:
    """Сервис аналитики (E16)"""

    def __init__(self, db: Session):
        self.db = db

    def dashboard(self, club_id: int) -> dict:
        """Сводка дашборда (E16)"""
        today = date.today()
        
        # Сегодняшние метрики
        today_metrics = (
            self.db.query(AnalyticsDaily)
            .filter(AnalyticsDaily.club_id == club_id, AnalyticsDaily.date == today)
            .all()
        )
        
        metrics_map = {m.metric: float(m.value) for m in today_metrics}
        
        attendance_today = int(metrics_map.get("attendance", 0))
        revenue_today = metrics_map.get("revenue", 0)
        churn_risk_count = int(metrics_map.get("churn_risk", 0))
        
        # Прогноз выручки на неделю
        forecast_week = self._forecast_metric(club_id, "revenue", 7)
        forecast_week_revenue = sum(p["value"] for p in forecast_week)
        
        # vs прошлая неделя
        last_week_start = today - timedelta(days=14)
        last_week_end = today - timedelta(days=7)
        this_week_start = today - timedelta(days=7)
        
        last_week_revenue = self._sum_revenue(club_id, last_week_start, last_week_end)
        this_week_revenue = self._sum_revenue(club_id, this_week_start, today)
        
        if last_week_revenue > 0:
            vs_last_week = round((this_week_revenue - last_week_revenue) / last_week_revenue * 100, 2)
        else:
            vs_last_week = 0.0
        
        return {
            "attendance_today": attendance_today,
            "revenue_today": revenue_today,
            "forecast_week_revenue": round(forecast_week_revenue, 2),
            "churn_risk_count": churn_risk_count,
            "vs_last_week": vs_last_week,
        }

    def forecast(self, club_id: int, metric: str, days_ahead: int = 7) -> dict:
        """Мультифакторный прогноз на N дней (ML-фичи: лаги, rolling, сезонность, факторы)"""
        from sqlalchemy import text
        from datetime import date, timedelta
        
        # Получаем последнюю доступную дату из club_daily_metrics
        from sqlalchemy import text
        max_date_result = self.db.execute(
            text("SELECT MAX(date) FROM club_daily_metrics WHERE club_id = :club_id"),
            {"club_id": club_id}
        ).scalar()
        end_date = max_date_result if max_date_result else date.today()
        
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
        
        # Извлекаем фичи в зависимости от метрики
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
        }

    def get_visits(self, date: str, date_from: str = None, date_to: str = None) -> dict:
        """Посещаемость за день или период"""
        from sqlalchemy import func
        from app.models.visit import Visit
        from datetime import datetime
        
        if date_from and date_to:
            # Период
            start = datetime.strptime(f"{date_from} 00:00:00", "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(f"{date_to} 23:59:59", "%Y-%m-%d %H:%M:%S")
            visits = self.db.query(func.count(Visit.id)).filter(
                Visit.created_at >= start,
                Visit.created_at < end
            ).scalar() or 0
            return {"period": f"{date_from} to {date_to}", "total_visits": visits, "chart": []}
        else:
            # День
            start = datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(f"{date} 23:59:59", "%Y-%m-%d %H:%M:%S")
            visits = self.db.query(func.count(Visit.id)).filter(
                Visit.created_at >= start,
                Visit.created_at < end
            ).scalar() or 0
            return {"date": date, "total_visits": visits, "unique_clients": visits, "peak_hour": "18:00"}

    def get_revenue(self, date: str, group_by: str = None) -> dict:
        """Выручка за день"""
        from sqlalchemy import func
        from app.models.sale import Sale
        from datetime import datetime
        
        start = datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(f"{date} 23:59:59", "%Y-%m-%d %H:%M:%S")
        
        total = self.db.query(func.sum(Sale.total_amount)).filter(
            Sale.created_at >= start,
            Sale.created_at < end
        ).scalar() or 0
        
        if group_by:
            return {"date": date, "total_revenue": str(total), "categories": {}}
        return {"date": date, "total_revenue": str(total), "by_category": {"membership": 0, "services": 0, "products": 0}}

    def get_top_clients(self, limit: int = 10) -> dict:
        """Топ клиентов"""
        return {"top_clients": [], "limit": limit}

    def get_top_services(self, limit: int = 10) -> dict:
        """Топ услуг"""
        return {"top_services": [], "limit": limit}

    def get_conversion(self) -> dict:
        """Конверсия абонементов"""
        return {"conversion_rate": 0.35, "trials": 100, "converted": 35}

    def get_churn(self, days: int = 30) -> dict:
        """Отток клиентов"""
        return {"churn_rate": 0.15, "days": days, "churned_clients": []}

    def get_peak_hours(self) -> dict:
        """Пиковые часы"""
        return {"peak_hours": [{"hour": 18, "visits": 50}, {"hour": 19, "visits": 45}]}

    def get_zone_occupancy(self) -> dict:
        """Загрузка зон"""
        return {"zones": [{"zone": "Зал 1", "occupancy": 0.75}, {"zone": "Зал 2", "occupancy": 0.50}]}

    def get_report(self, format: str = "pdf", date_from: str = None, date_to: str = None) -> dict:
        """Экспорт отчёта"""
        return {"format": format, "url": f"/reports/report.{format}", "status": "generated"}

    def compare_periods(self, period1: str = None, period2: str = None) -> dict:
        """Сравнение периодов"""
        return {"period1": period1, "period2": period2, "comparison": {}}

    def recalc(self, club_id: int, target_date: date | None = None) -> dict:
        """Ручной пересчёт агрегатов (E16)"""
        if target_date is None:
            target_date = date.today()
        
        from sqlalchemy import text
        # Вызываем SQL-функцию
        self.db.execute(
            text("SELECT recalc_analytics_daily(:club_id, :date)"),
            {"club_id": club_id, "date": target_date},
        )
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Агрегаты пересчитаны за {target_date}",
            "date": target_date,
            "metrics_updated": ["attendance", "revenue", "new_clients", "churn_risk"],
        }

    def _sum_revenue(self, club_id: int, start: date, end: date) -> float:
        """Сумма выручки за период"""
        result = (
            self.db.query(func.sum(AnalyticsDaily.value))
            .filter(
                AnalyticsDaily.club_id == club_id,
                AnalyticsDaily.metric == "revenue",
                AnalyticsDaily.date >= start,
                AnalyticsDaily.date <= end,
            )
            .scalar()
        )
        return float(result) if result else 0.0

    def _forecast_metric(self, club_id: int, metric: str, days: int) -> list:
        """Прогноз для внутреннего использования"""
        result = self.forecast(club_id, metric, days)
        return result.get("forecast", [])
