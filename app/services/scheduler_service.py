# app/services/scheduler_service.py
from datetime import datetime, timezone, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService


class AnalyticsScheduler:
    """Планировщик ежедневного пересчёта аналитики (TS-012)"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Настройка задач"""
        # Ежедневно в 00:05 — пересчёт "вчера" + прогноз
        self.scheduler.add_job(
            self._daily_recalc,
            CronTrigger(hour=0, minute=5),
            id="daily_analytics",
            name="Daily analytics recalc + forecast",
            replace_existing=True,
        )
        print("[Scheduler] Daily analytics job scheduled at 00:05")

    def _daily_recalc(self):
        """Пересчёт агрегатов за вчера + прогноз на 7 дней"""
        db = SessionLocal()
        try:
            yesterday = date.today() - timedelta(days=1)
            
            # Пересчёт за вчера
            service = AnalyticsService(db)
            result = service.recalc(1, yesterday)
            print(f"[Scheduler] Daily recalc: {result['message']}")
            
            # Прогноз на 7 дней
            for metric in ['attendance', 'revenue', 'new_clients', 'churn_risk']:
                forecast = service.forecast(1, metric, 7)
                print(f"[Scheduler] Forecast {metric}: {forecast['trend']}")
                
        except Exception as e:
            print(f"[Scheduler] ERROR: {e}")
        finally:
            db.close()

    def start(self):
        """Запустить планировщик"""
        self.scheduler.start()
        print("[Scheduler] Started")

    def shutdown(self):
        """Остановить планировщик"""
        self.scheduler.shutdown()
        print("[Scheduler] Shutdown")


# Глобальный экземпляр
_analytics_scheduler = None


def start_analytics_scheduler():
    """Запустить при старте приложения"""
    global _analytics_scheduler
    if _analytics_scheduler is None:
        _analytics_scheduler = AnalyticsScheduler()
        _analytics_scheduler.start()
    return _analytics_scheduler


def shutdown_analytics_scheduler():
    """Остановить при завершении"""
    global _analytics_scheduler
    if _analytics_scheduler:
        _analytics_scheduler.shutdown()
        _analytics_scheduler = None
