# app/services/email_queue_service.py
"""A4: очередь email-писем.

- Таблица email_queue (авто-миграция, как остальные runtime-DDL).
- enqueue() — постановка в очередь вместо мгновенной «успешной» отправки.
- process_queue() — отправка due-писем через SMTPEmailService (конфиг из
  notification_settings: smtp_host/port/user/password/ssl, from_email),
  ретраи 1 мин -> 5 мин -> 15 мин, после max_attempts -> FAILED.
- Пока SMTP не настроен/недоступен письма копятся со статусом PENDING
  (критерий приёмки A4: при выключенном SMTP письмо копится и уходит после включения).
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

_BACKOFF_SECONDS = (60, 300, 900)   # экспоненциальные паузы между попытками

_DDL_DONE = False


def ensure_email_queue(db: Session):
    global _DDL_DONE
    if _DDL_DONE:
        return
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS email_queue ("
        " id VARCHAR(36) PRIMARY KEY,"
        " recipient VARCHAR(255) NOT NULL,"
        " subject VARCHAR(500) NOT NULL,"
        " body TEXT,"
        " html_body TEXT,"
        " priority INTEGER DEFAULT 3,"
        " status VARCHAR(10) DEFAULT 'PENDING',"
        " attempts INTEGER DEFAULT 0,"
        " max_attempts INTEGER DEFAULT 3,"
        " last_error TEXT,"
        " next_attempt_at TIMESTAMP,"
        " created_at TIMESTAMP,"
        " sent_at TIMESTAMP)"))
    db.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status)"))
    db.commit()
    _DDL_DONE = True


class EmailQueueService:
    def __init__(self, db: Session):
        self.db = db
        ensure_email_queue(db)

    # ---------- постановка в очередь ----------
    def enqueue(self, recipient: str, subject: str, body: str,
                html_body: str | None = None, priority: int = 3,
                max_attempts: int = 3) -> str:
        eid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO email_queue (id, recipient, subject, body, html_body,"
            " priority, status, attempts, max_attempts, created_at)"
            " VALUES (:i, :r, :s, :b, :h, :p, 'PENDING', 0, :m, :n)"),
            {"i": eid, "r": recipient, "s": subject, "b": body, "h": html_body,
             "p": priority, "m": max_attempts, "n": datetime.now(timezone.utc)})
        self.db.commit()
        return eid

    # ---------- конфиг SMTP из настроек «Уведомлений» ----------
    def smtp_config(self) -> dict:
        row = self.db.execute(text(
            "SELECT config FROM notification_settings WHERE id=1")).first()
        cfg = {}
        if row and row[0]:
            try:
                cfg = json.loads(row[0])
            except Exception:
                pass
        return {
            "host": cfg.get("smtp_host") or "",
            "port": int(cfg.get("smtp_port") or 465),
            "user": cfg.get("smtp_user") or "",
            "password": cfg.get("smtp_password") or "",
            "use_ssl": str(cfg.get("smtp_ssl", True)).lower() in ("1", "true", "yes"),
            "from_email": (cfg.get("from_email") or cfg.get("smtp_user")
                           or "no-reply@fitintel.ru"),
        }

    # ---------- доставка ----------
    def _deliver(self, cfg: dict, recipient: str, subject: str,
                 body: str, html_body: str | None):
        if not cfg.get("host"):
            raise RuntimeError("SMTP не настроен: укажите smtp_host в «Уведомления → Настройки»")
        from app.services.email_service import SMTPEmailService
        svc = SMTPEmailService(
            host=cfg["host"], port=cfg["port"],
            username=cfg["user"] or None, password=cfg["password"] or None,
            use_ssl=cfg["use_ssl"], from_email=cfg["from_email"],
        )
        svc.send(subject=subject, body=body, recipients=[recipient],
                 html_body=html_body)

    # ---------- процессинг очереди ----------
    def process_queue(self, limit: int = 20) -> dict:
        cfg = self.smtp_config()
        now = datetime.now(timezone.utc)
        rows = self.db.execute(text(
            "SELECT id, recipient, subject, body, html_body, attempts, max_attempts"
            " FROM email_queue"
            " WHERE status = 'PENDING'"
            "   AND (next_attempt_at IS NULL OR next_attempt_at <= :n)"
            " ORDER BY priority ASC, created_at ASC LIMIT :l"),
            {"n": now, "l": limit}).fetchall()
        sent = failed = deferred = 0
        for r in rows:
            try:
                self._deliver(cfg, r.recipient, r.subject, r.body, r.html_body)
                self.db.execute(text(
                    "UPDATE email_queue SET status='SENT', sent_at=:n, last_error=NULL"
                    " WHERE id=:i"), {"n": now, "i": r.id})
                sent += 1
            except Exception as e:
                attempts = (r.attempts or 0) + 1
                err = str(e)[:300]
                if attempts >= (r.max_attempts or 3):
                    self.db.execute(text(
                        "UPDATE email_queue SET status='FAILED', attempts=:a, last_error=:e"
                        " WHERE id=:i"), {"a": attempts, "e": err, "i": r.id})
                    failed += 1
                else:
                    backoff = _BACKOFF_SECONDS[min(attempts - 1, len(_BACKOFF_SECONDS) - 1)]
                    nxt = now + timedelta(seconds=backoff)
                    self.db.execute(text(
                        "UPDATE email_queue SET attempts=:a, last_error=:e,"
                        " next_attempt_at=:x WHERE id=:i"),
                        {"a": attempts, "e": err, "x": nxt, "i": r.id})
                    deferred += 1
        self.db.commit()
        return {"processed": len(rows), "sent": sent, "failed": failed, "deferred": deferred}
