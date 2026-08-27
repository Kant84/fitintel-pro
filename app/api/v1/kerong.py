"""E60: Auto-Scheduler — автоматические напоминания без участия сотрудников."""
import uuid
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

class AutoScheduler:
    def __init__(self, db: Session):
        self.db = db
        self.notifications_created = 0
    
    def run_daily(self) -> Dict[str, int]:
        results = {
            "subscription_expiry": 0,
            "churn_prevention": 0,
            "birthday_greeting": 0,
            "payment_reminder": 0,
        }
        results["subscription_expiry"] = self._notify_subscription_expiry()
        results["churn_prevention"] = self._notify_churn_risk()
        results["birthday_greeting"] = self._notify_birthdays()
        return results
    
    def _notify_subscription_expiry(self, days_before: int = 3) -> int:
        target_date = date.today() + timedelta(days=days_before)
        sql = text("""
            SELECT s.id, s.client_id, c.first_name, c.phone, s.end_date, t.name as tariff_name
            FROM subscriptions s
            JOIN clients c ON s.client_id = c.id
            LEFT JOIN tariffs t ON s.tariff_id = t.id
            WHERE s.status = 'active'
            AND s.end_date = :target
            AND s.auto_renew = false
            AND NOT EXISTS (
                SELECT 1 FROM notifications n
                WHERE n.client_id = s.client_id
                AND n.type = 'subscription_expiry'
                AND n.created_at > NOW() - INTERVAL '7 days'
            )
        """)
        rows = self.db.execute(sql, {"target": target_date}).fetchall()
        count = 0
        for row in rows:
            tariff = row[5] or "ваш абонемент"
            self._create_notification(
                client_id=str(row[1]),
                type_="subscription_expiry",
                title="Абонемент скоро закончится",
                message=f"{row[2]}, ваш абонемент '{tariff}' заканчивается {row[4]}. Продлите сейчас!",
                channel="sms",
                send_at="09:00",
            )
            count += 1
        self.db.commit()
        return count
    
    def _notify_churn_risk(self, inactive_days: int = 14) -> int:
        since = datetime.now() - timedelta(days=inactive_days)
        sql = text("""
            SELECT c.id, c.first_name, c.phone, MAX(v.entry_time) as last_visit
            FROM clients c
            LEFT JOIN visits v ON c.id = v.client_id
            JOIN subscriptions s ON c.id = s.client_id
            WHERE s.status = 'active'
            AND s.end_date > NOW()
            GROUP BY c.id, c.first_name, c.phone
            HAVING MAX(v.entry_time) < :since OR MAX(v.entry_time) IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM notifications n
                WHERE n.client_id = c.id
                AND n.type = 'churn_prevention'
                AND n.created_at > NOW() - INTERVAL '7 days'
            )
        """)
        rows = self.db.execute(sql, {"since": since}).fetchall()
        count = 0
        for row in rows:
            self._create_notification(
                client_id=str(row[0]),
                type_="churn_prevention",
                title="Возвращайтесь со скидкой 20%",
                message=f"{row[1]}, мы скучаем! Ваша персональная скидка 20% на любой абонемент. Ждём вас!",
                channel="sms",
                send_at="18:00",
            )
            count += 1
        self.db.commit()
        return count
    
    def _notify_birthdays(self) -> int:
        today = date.today()
        sql = text("""
            SELECT id, first_name, phone, birth_date
            FROM clients
            WHERE EXTRACT(MONTH FROM birth_date) = :month
            AND EXTRACT(DAY FROM birth_date) = :day
            AND phone IS NOT NULL
        """)
        rows = self.db.execute(sql, {"month": today.month, "day": today.day}).fetchall()
        count = 0
        for row in rows:
            self._create_notification(
                client_id=str(row[0]),
                type_="birthday",
                title="С днем рождения!",
                message=f"{row[1]}, поздравляем! Подарок — бесплатное посещение сауны при покупке абонемента.",
                channel="sms",
                send_at="10:00",
            )
            count += 1
        self.db.commit()
        return count
    
    def _create_notification(self, client_id: str, type_: str, title: str,
                             message: str, channel: str = "sms", send_at: Optional[str] = None):
        sql = text("""
            INSERT INTO notifications (id, client_id, type, title, message, channel, status, scheduled_at, created_at)
            VALUES (:id, :client_id, :type, :title, :message, :channel, 'pending', :scheduled, NOW())
        """)
        self.db.execute(sql, {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "type": type_,
            "title": title,
            "message": message,
            "channel": channel,
            "scheduled": send_at,
        })
