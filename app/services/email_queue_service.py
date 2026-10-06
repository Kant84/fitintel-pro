# app/services/email_queue_service.py
"""A4: очередь email. Копится при выключенном SMTP, уходит процессингом."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_ATTEMPTS = 3
RETRY_DELAYS_MIN = (1, 5, 15)


def _now():
    return datetime.now(timezone.utc)


def ensure_email_queue(db: Session) -> None:
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS email_queue ("
        " id VARCHAR(36) PRIMARY KEY,"
        " recipient VARCHAR(320) NOT NULL,"
        " subject VARCHAR(500) NOT NULL,"
        " body TEXT,"
        " status VARCHAR(20) NOT NULL DEFAULT 'PENDING',"
        " attempts INTEGER NOT NULL DEFAULT 0,"
        " next_attempt_at TIMESTAMP,"
        " last_error TEXT,"
        " created_at TIMESTAMP,"
        " sent_at TIMESTAMP)"))
    db.commit()
    # миграция: старые БД создавались без колонки profile
    try:
        db.execute(text(
            "ALTER TABLE email_queue ADD COLUMN IF NOT EXISTS"
            " profile VARCHAR(20) NOT NULL DEFAULT 'club'"))
        db.commit()
    except Exception:
        db.rollback()   # SQLite: ADD COLUMN IF NOT EXISTS не поддерживается — ок


class EmailQueueService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- настройки SMTP читаем ТОЙ ЖЕ сессией (важно для тестов) ----------
    def _smtp_config(self):
        try:
            row = self.db.execute(text(
                "SELECT * FROM notification_settings WHERE id=1")).mappings().first()
        except Exception:
            return None
        if not row:
            return None
        host = row.get("smtp_host")
        if not host:
            return None
        port = int(row.get("smtp_port") or 465)
        return {"host": host, "port": port,
                "user": row.get("smtp_user"),
                "password": row.get("smtp_pass"),
                "from": row.get("email_from") or row.get("smtp_user"),
                "ssl": port == 465}

    # ---------- постановка в очередь ----------
    def enqueue(self, recipient, subject, body, html_body=None, max_attempts=MAX_ATTEMPTS):
        ensure_email_queue(self.db)
        self.db.execute(text(
            "INSERT INTO email_queue (id, recipient, subject, body, status, attempts,"
            " next_attempt_at, created_at) VALUES (:id, :r, :s, :b, 'PENDING', 0, :na, :ca)"),
            {"id": str(uuid.uuid4()), "r": recipient, "s": subject, "b": body,
             "na": _now(), "ca": _now()})
        self.db.commit()
        return True

    # ---------- процессинг ----------
    def process_queue(self, limit=50):
        ensure_email_queue(self.db)
        cfg = self._smtp_config()
        rows = self.db.execute(text(
            "SELECT id, recipient, subject, body, attempts FROM email_queue"
            " WHERE status='PENDING' AND (next_attempt_at IS NULL OR next_attempt_at <= :now)"
            " ORDER BY created_at LIMIT :lim"), {"now": _now(), "lim": int(limit)}).fetchall()
        sent = failed = waiting = 0
        for rid, recipient, subject, body, attempts in rows:
            if not cfg:
                waiting += 1
                continue
            try:
                self._deliver(cfg, recipient, subject, body, None)
                self.db.execute(text(
                    "UPDATE email_queue SET status='SENT', sent_at=:n, last_error=NULL"
                    " WHERE id=:id"), {"n": _now(), "id": rid})
                sent += 1
            except Exception as e:
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    self.db.execute(text(
                        "UPDATE email_queue SET status='FAILED', attempts=:a, last_error=:e"
                        " WHERE id=:id"), {"a": attempts, "e": str(e)[:500], "id": rid})
                    failed += 1
                else:
                    delay = RETRY_DELAYS_MIN[min(attempts - 1, len(RETRY_DELAYS_MIN) - 1)]
                    self.db.execute(text(
                        "UPDATE email_queue SET attempts=:a, last_error=:e, next_attempt_at=:na"
                        " WHERE id=:id"), {"a": attempts, "e": str(e)[:500],
                                           "na": _now() + timedelta(minutes=delay), "id": rid})
                    waiting += 1
            self.db.commit()
        return {"processed": len(rows), "sent": sent, "failed": failed, "waiting_smtp": waiting}

    def _deliver(self, cfg, recipient, subject, body, html_body):
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        msg["From"] = cfg.get("from") or cfg.get("user") or "FitIntel PRO"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body or body or "", "html", "utf-8"))
        if cfg.get("ssl"):
            srv = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20)
        else:
            srv = smtplib.SMTP(cfg["host"], cfg["port"], timeout=20)
            srv.starttls()
        try:
            if cfg.get("user"):
                srv.login(cfg["user"], cfg.get("password") or "")
            srv.send_message(msg)
        finally:
            srv.quit()