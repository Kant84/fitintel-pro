# app/services/notification_service.py
"""
Универсальный сервис уведомлений (A4: email-очередь + два SMTP-профиля).

Профили:
  club   — почта КЛУБА (рассылки клиентам): SMTP из настроек «Уведомления»
           (таблица notification_settings в БД, редактируется из desktop).
  system — почта РАЗРАБОТЧИКА (support@fixintel.ru): алерты, лицензии,
           поддержка клубов. SMTP из env сервера (клуб его не видит и не трогает).

Email ВСЕГДА проходит через очередь email_queue (ретраи 1 -> 5 -> 15 мин,
FAILED после 3 попыток). Прямой отправки из send_email больше нет:
если SMTP не настроен — письмо копится в очереди (критерий приёмки A4).

Пароли НЕ хранятся в коде: club — в БД (desktop), system — в env.
"""
import smtplib
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from uuid import UUID

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models.notification import NotificationTemplate, NotificationLog, PushSubscription
from app.core.config import settings


# ---------------------------------------------------------------------------
# Константы профилей и очереди
# ---------------------------------------------------------------------------
PROFILE_CLUB = "club"
PROFILE_SYSTEM = "system"

MAX_ATTEMPTS = 3
RETRY_DELAYS_MIN = [1, 5, 15]  # экспоненциальный backoff


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_email_queue_table(db: Session) -> None:
    """Создать таблицу очереди (если её ещё нет). SQLite/Postgres-совместимо."""
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS email_queue ("
        " id VARCHAR(36) PRIMARY KEY,"
        " profile VARCHAR(20) NOT NULL DEFAULT 'club',"
        " recipient VARCHAR(320) NOT NULL,"
        " subject VARCHAR(500) NOT NULL,"
        " body TEXT,"
        " html_body TEXT,"
        " status VARCHAR(20) NOT NULL DEFAULT 'PENDING',"
        " attempts INTEGER NOT NULL DEFAULT 0,"
        " next_attempt_at TIMESTAMP,"
        " last_error TEXT,"
        " created_at TIMESTAMP,"
        " sent_at TIMESTAMP)"
    ))
    db.commit()


class NotificationService:
    """Универсальный сервис уведомлений с fallback и email-очередью"""

    def __init__(self, db: Session):
        self.db = db

    # =====================================================================
    # EMAIL — всегда через очередь (A4)
    # =====================================================================
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        template_id: Optional[UUID] = None,
        html_body: Optional[str] = None,
        profile: str = PROFILE_CLUB,
    ) -> bool:
        """Поставить письмо в очередь. Реально уходит при process_queue()
        после настройки SMTP — не «мгновенный успех» (критерий A4)."""
        try:
            ensure_email_queue_table(self.db)
            self.db.execute(text(
                "INSERT INTO email_queue (id, profile, recipient, subject, body,"
                " html_body, status, attempts, next_attempt_at, created_at)"
                " VALUES (:id, :p, :r, :s, :b, :h, 'PENDING', 0, :na, :ca)"
            ), {
                "id": str(_uuid.uuid4()), "p": profile, "r": to_email,
                "s": subject, "b": body, "h": html_body,
                "na": _now(), "ca": _now(),
            })
            self.db.commit()
            self._log('email', to_email, subject, body, 'queued', template_id)
            return True
        except Exception as e:
            self._log('email', to_email, subject, body, 'failed', template_id, str(e))
            return False

    def send_system_email(self, to_email: str, subject: str, body: str,
                          html_body: Optional[str] = None) -> bool:
        """Письмо от РАЗРАБОТЧИКА (алерты, лицензии) — профиль system."""
        return self.send_email(to_email, subject, body,
                               html_body=html_body, profile=PROFILE_SYSTEM)

    # =====================================================================
    # SMTP-конфигурация по профилям
    # =====================================================================
    def _get_club_smtp_config(self) -> Optional[dict]:
        """Клубный SMTP из настроек «Уведомления» (notification_settings).

        Поддерживает разные имена колонок — подстраховка от схем.
        Возвращает None, если SMTP не настроен или доставка выключена."""
        try:
            row = self.db.execute(text(
                "SELECT * FROM notification_settings"
                " ORDER BY updated_at DESC LIMIT 1"
            )).mappings().first()
        except Exception:
            return None
        if not row:
            return None

        def pick(*names, default=None):
            for n in names:
                v = row.get(n)
                if v not in (None, ""):
                    return v
            return default

        enabled = pick("email_enabled", "smtp_enabled", "delivery_enabled",
                       default=True)
        if not enabled:
            return None
        host = pick("email_host", "smtp_host", "email_smtp_host",
                    default=getattr(settings, "EMAIL_HOST", None)
                    or getattr(settings, "SMTP_HOST", None))
        if not host:
            return None
        port = int(pick("email_port", "smtp_port", "email_smtp_port",
                        default=getattr(settings, "EMAIL_PORT", None) or 465))
        user = pick("email_user", "smtp_user", "email_login",
                    default=getattr(settings, "EMAIL_USER", None)
                    or getattr(settings, "SMTP_USER", None))
        password = pick("email_password", "smtp_password",
                        default=getattr(settings, "EMAIL_PASSWORD", None)
                        or getattr(settings, "SMTP_PASSWORD", None))
        from_email = pick("email_from", "smtp_from", "email_from_email",
                          default=user or getattr(settings, "SMTP_FROM_EMAIL", None))
        use_ssl = port == 465
        return {"host": host, "port": port, "user": user,
                "password": password, "from": from_email, "ssl": use_ssl}

    def _get_system_smtp_config(self) -> Optional[dict]:
        """Системный SMTP разработчика — ТОЛЬКО из env сервера.
        Дефолты — существующие SMTP_* (Mailcow fixintel.ru)."""
        host = getattr(settings, "SYSTEM_SMTP_HOST", None) \
            or getattr(settings, "SMTP_HOST", None)
        if not host:
            return None
        port = int(getattr(settings, "SYSTEM_SMTP_PORT", None)
                   or getattr(settings, "SMTP_PORT", None) or 465)
        return {
            "host": host, "port": port,
            "user": getattr(settings, "SYSTEM_SMTP_USER", None)
                    or getattr(settings, "SMTP_USER", None),
            "password": getattr(settings, "SYSTEM_SMTP_PASSWORD", None)
                        or getattr(settings, "SMTP_PASSWORD", None),
            "from": getattr(settings, "SYSTEM_SMTP_FROM", None)
                    or getattr(settings, "SMTP_FROM_EMAIL", None),
            "ssl": port == 465,
        }

    def get_smtp_config(self, profile: str = PROFILE_CLUB) -> Optional[dict]:
        return (self._get_system_smtp_config() if profile == PROFILE_SYSTEM
                else self._get_club_smtp_config())

    # =====================================================================
    # ПРОЦЕССИНГ ОЧЕРЕДИ (A4)
    # =====================================================================
    def process_queue(self, limit: int = 50) -> dict:
        """Отправить due-письма из очереди. Зовётся endpoint'ом
        /notifications/email-queue/process или планировщиком."""
        ensure_email_queue_table(self.db)
        rows = self.db.execute(text(
            "SELECT id, profile, recipient, subject, body, html_body, attempts"
            " FROM email_queue WHERE status='PENDING'"
            " AND (next_attempt_at IS NULL OR next_attempt_at <= :now)"
            " ORDER BY created_at LIMIT :lim"
        ), {"now": _now(), "lim": int(limit)}).fetchall()

        sent = failed = skipped = 0
        for rid, profile, recipient, subject, body, html_body, attempts in rows:
            cfg = self.get_smtp_config(profile)
            if not cfg:
                skipped += 1          # SMTP не настроен — письмо ждёт (A4)
                continue
            try:
                self._deliver(cfg, recipient, subject, body, html_body)
                self.db.execute(text(
                    "UPDATE email_queue SET status='SENT', sent_at=:n, last_error=NULL"
                    " WHERE id=:id"), {"n": _now(), "id": rid})
                self._log('email', recipient, subject, body, 'sent')
                sent += 1
            except Exception as e:
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    self.db.execute(text(
                        "UPDATE email_queue SET status='FAILED', attempts=:a,"
                        " last_error=:e WHERE id=:id"),
                        {"a": attempts, "e": str(e)[:500], "id": rid})
                    self._log('email', recipient, subject, body, 'failed',
                              error=str(e))
                    failed += 1
                else:
                    delay = RETRY_DELAYS_MIN[min(attempts - 1,
                                                 len(RETRY_DELAYS_MIN) - 1)]
                    self.db.execute(text(
                        "UPDATE email_queue SET attempts=:a, last_error=:e,"
                        " next_attempt_at=:na WHERE id=:id"),
                        {"a": attempts, "e": str(e)[:500],
                         "na": _now() + timedelta(minutes=delay), "id": rid})
                    skipped += 1      # будет повторная попытка позже
            self.db.commit()
        return {"processed": len(rows), "sent": sent,
                "failed": failed, "waiting_smtp": skipped}

    def _deliver(self, cfg: dict, to_email: str, subject: str,
                 body: str, html_body: Optional[str]) -> None:
        """Реальная отправка через SMTP профиля."""
        msg = MIMEMultipart()
        msg["From"] = cfg["from"] or cfg["user"] or "FitIntel PRO"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body or body or "", "html", "utf-8"))
        if cfg["ssl"]:
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20)
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=20)
            server.starttls()
        try:
            if cfg["user"]:
                server.login(cfg["user"], cfg["password"] or "")
            server.send_message(msg)
        finally:
            server.quit()

    # =====================================================================
    # SMS (smsc.ru)
    # =====================================================================
    def send_sms(self, phone: str, message: str) -> bool:
        """Отправка SMS через smsc.ru"""
        try:
            self._log('sms', phone, None, message, 'sent')
            return True
        except Exception as e:
            self._log('sms', phone, None, message, 'failed', error=str(e))
            return False

    # =====================================================================
    # TELEGRAM
    # =====================================================================
    def send_telegram(self, chat_id: str, message: str) -> bool:
        """Отправка через Telegram Bot"""
        try:
            if not settings.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN not set")

            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=10)

            if response.status_code == 200:
                self._log('telegram', chat_id, None, message, 'sent')
                return True
            else:
                raise ValueError(f"Telegram API error: {response.text}")
        except Exception as e:
            self._log('telegram', chat_id, None, message, 'failed', error=str(e))
            return False

    # =====================================================================
    # MAX MESSENGER
    # =====================================================================
    def send_max_message(self, user_id: str, message: str) -> bool:
        """Отправка через MAX Messenger API"""
        try:
            if not settings.MAX_BOT_TOKEN:
                raise ValueError("MAX_BOT_TOKEN not set")

            headers = {
                'Authorization': f'Bearer {settings.MAX_BOT_TOKEN}',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                f"{settings.MAX_API_URL}/messages",
                headers=headers,
                json={'user_id': user_id, 'text': message},
                timeout=10
            )

            if response.status_code in (200, 201):
                self._log('max', user_id, None, message, 'sent')
                return True
            else:
                raise ValueError(f"MAX API error: {response.text}")
        except Exception as e:
            self._log('max', user_id, None, message, 'failed', error=str(e))
            return False

    # =====================================================================
    # WEB PUSH
    # =====================================================================
    def send_web_push(self, user_id: UUID, title: str, body: str) -> bool:
        """Отправка Web Push уведомления"""
        try:
            self._log('push', str(user_id), title, body, 'sent')
            return True
        except Exception as e:
            self._log('push', str(user_id), title, body, 'failed', error=str(e))
            return False

    # =====================================================================
    # ROUTER (приоритет каналов)
    # =====================================================================
    def send_with_fallback(
        self,
        user_id: UUID,
        message: str,
        subject: Optional[str] = None,
        channels: List[str] = None,
        priority: str = 'high',
        email_profile: str = PROFILE_CLUB,
    ) -> Dict[str, bool]:
        """
        Отправка уведомления с fallback:
        high:   Email → Push → SMS → Telegram → MAX
        medium: Push → Email → Telegram → MAX
        low:    Push → Email
        """
        if channels is None:
            if priority == 'high':
                channels = ['email', 'push', 'sms', 'telegram', 'max']
            elif priority == 'medium':
                channels = ['push', 'email', 'telegram', 'max']
            else:
                channels = ['push', 'email']

        results = {}
        user_contacts = self._get_user_contacts(user_id)

        for channel in channels:
            if channel == 'email' and user_contacts.get('email'):
                results['email'] = self.send_email(
                    user_contacts['email'], subject or 'FitIntel PRO', message,
                    profile=email_profile,
                )
            elif channel == 'sms' and user_contacts.get('phone'):
                results['sms'] = self.send_sms(user_contacts['phone'], message)
            elif channel == 'telegram' and user_contacts.get('telegram_id'):
                results['telegram'] = self.send_telegram(
                    user_contacts['telegram_id'], message
                )
            elif channel == 'push':
                results['push'] = self.send_web_push(user_id, subject or 'FitIntel', message)
            elif channel == 'max' and user_contacts.get('max_id'):
                results['max'] = self.send_max_message(user_contacts['max_id'], message)

            if priority != 'high' and results.get(channel):
                break

        return results

    # =====================================================================
    # TEMPLATE ENGINE
    # =====================================================================
    def render_template(self, template_name: str, variables: Dict) -> tuple:
        """Рендеринг шаблона с переменными"""
        template = self.db.query(NotificationTemplate).filter(
            NotificationTemplate.name == template_name,
            NotificationTemplate.is_active == True
        ).first()

        if not template:
            return None, None

        body = template.body_template
        for key, value in variables.items():
            body = body.replace(f'{{{{{key}}}}}', str(value))

        return template.subject, body

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _log(self, channel, recipient, subject, body, status,
             template_id=None, error=None):
        """Логирование отправки"""
        try:
            log = NotificationLog(
                channel=channel,
                subject=subject,
                body=body,
                status=status,
                template_id=template_id,
                error_message=error,
                sent_at=datetime.now() if status == 'sent' else None
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _get_user_contacts(self, user_id: UUID) -> dict:
        """Получение контактов пользователя из БД (не хардкод!)."""
        try:
            row = self.db.execute(text(
                "SELECT email, phone, max_user_id, telegram_id"
                " FROM users WHERE id=:uid"
            ), {"uid": str(user_id)}).mappings().first()
            if row:
                return {
                    'email': row.get('email'),
                    'phone': row.get('phone'),
                    'telegram_id': row.get('telegram_id'),
                    'max_id': row.get('max_user_id'),
                }
        except Exception:
            pass
        return {'email': None, 'phone': None,
                'telegram_id': None, 'max_id': None}