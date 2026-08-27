"""E60: Feature Store — центральное хранилище признаков для ML-моделей."""
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, func

FEATURE_SCHEMA = {
    "client_churn": [
        "visits_30d", "payments_90d", "last_visit_days",
        "subscription_type", "subscription_days_left", "total_spent"
    ],
    "optimal_price": [
        "club_location", "season", "competitor_price", "occupancy_rate", "avg_client_income"
    ],
    "best_send_time": [
        "hour_open_rate", "day_of_week", "client_age", "subscription_type"
    ],
    "fraud_score": [
        "amount", "payment_method", "time_of_day", "client_history_length", "refund_count"
    ],
    "trainer_load": [
        "bookings_count", "cancel_rate", "client_rating", "hours_worked_week"
    ],
}

class FeatureStore:
    """Извлекает признаки из БД для ML-моделей."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_client_features(self, client_id: str) -> Dict[str, Any]:
        """Извлечь все признаки клиента."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)
        
        # Визиты за 30 дней
        visits_30d = self.db.execute(text("""
            SELECT COUNT(*) FROM visits
            WHERE client_id = :cid AND entry_time >= :since
        """), {"cid": client_id, "since": thirty_days_ago}).scalar() or 0
        
        # Последний визит (дней назад)
        last_visit = self.db.execute(text("""
            SELECT entry_time FROM visits
            WHERE client_id = :cid ORDER BY entry_time DESC LIMIT 1
        """), {"cid": client_id}).fetchone()
        if last_visit and last_visit[0]:
            lv = last_visit[0]
            if lv.tzinfo is None:
                lv = lv.replace(tzinfo=timezone.utc)
            last_visit_days = (now - lv).days
        else:
            last_visit_days = 999
        
        # Платежи за 90 дней
        payments_90d = self.db.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM payments
            WHERE client_id = :cid AND created_at >= :since
        """), {"cid": client_id, "since": ninety_days_ago}).fetchone()
        payment_count = payments_90d[0] if payments_90d else 0
        total_spent = float(payments_90d[1]) if payments_90d else 0.0
        
        # Активная подписка с JOIN к tariffs
        sub = self.db.execute(text("""
            SELECT t.name, s.end_date, s.status
            FROM subscriptions s
            LEFT JOIN tariffs t ON s.tariff_id = t.id
            WHERE s.client_id = :cid AND s.status = :active
            ORDER BY s.end_date DESC LIMIT 1
        """), {"cid": client_id, "active": "active"}).fetchone()
        
        subscription_type = sub[0] if sub else "none"
        subscription_days_left = (sub[1] - date.today()).days if sub and sub[1] else 0
        
        return {
            "visits_30d": visits_30d,
            "payments_90d": payment_count,
            "last_visit_days": last_visit_days,
            "subscription_type": subscription_type,
            "subscription_days_left": subscription_days_left,
            "total_spent": total_spent,
        }
    
    def get_churn_features(self, client_id: str) -> List[float]:
        """Вернуть вектор признаков для модели оттока."""
        f = self.get_client_features(client_id)
        return [
            float(f["visits_30d"]),
            float(f["payments_90d"]),
            float(f["last_visit_days"]),
            float(f["subscription_days_left"]),
            float(f["total_spent"]),
        ]
