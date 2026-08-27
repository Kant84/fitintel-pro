"""E60: Self-Heal — автоматическое исправление ошибок в БД."""
from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text

class SelfHeal:
    """Самоисцеляющийся модуль БД."""

    def __init__(self, db: Session):
        self.db = db

    def run_all(self) -> Dict[str, int]:
        results = {
            "gender_fixed": self._fix_gender_enum(),
            "phones_fixed": self._fix_empty_phones(),
            "emails_fixed": self._fix_empty_emails(),
            "duplicates_found": self._find_duplicate_clients(),
            "orphan_subs": self._fix_orphan_subscriptions(),
            "expired_creds": self._expire_old_credentials(),
        }
        self.db.commit()
        return results

    def _fix_gender_enum(self) -> int:
        fixes = [
            ("Не_указан", "НЕ_УКАЗАН"),
            ("не указан", "НЕ_УКАЗАН"),
            ("male", "MALE"),
            ("female", "FEMALE"),
            ("мужской", "MALE"),
            ("женский", "FEMALE"),
        ]
        total = 0
        for old, new in fixes:
            sql = text("UPDATE clients SET gender = :new WHERE gender = :old")
            result = self.db.execute(sql, {"new": new, "old": old})
            total += result.rowcount
        return total

    def _fix_empty_phones(self) -> int:
        sql = text("UPDATE clients SET phone = :placeholder WHERE phone IS NULL OR phone = :empty")
        result = self.db.execute(sql, {"placeholder": "+7(000)000-00-00", "empty": ""})
        return result.rowcount

    def _fix_empty_emails(self) -> int:
        sql = text("UPDATE clients SET email = :placeholder WHERE email IS NULL OR email = :empty")
        result = self.db.execute(sql, {"placeholder": "no-email@placeholder.com", "empty": ""})
        return result.rowcount

    def _find_duplicate_clients(self) -> int:
        sql = text("SELECT phone, COUNT(*) FROM clients WHERE phone IS NOT NULL AND phone != :empty GROUP BY phone HAVING COUNT(*) > 1")
        rows = self.db.execute(sql, {"empty": ""}).fetchall()
        return len(rows)

    def _fix_orphan_subscriptions(self) -> int:
        sql = text("UPDATE subscriptions SET status = :cancelled, updated_at = NOW() WHERE client_id NOT IN (SELECT id FROM clients) AND status != :cancelled")
        result = self.db.execute(sql, {"cancelled": "cancelled"})
        return result.rowcount

    def _expire_old_credentials(self) -> int:
        """Деактивировать credentials с истёкшим valid_until."""
        sql = text("UPDATE credentials SET status = :expired, updated_at = NOW() WHERE valid_until < NOW() AND status = :active")
        result = self.db.execute(sql, {"expired": "expired", "active": "active"})
        return result.rowcount
