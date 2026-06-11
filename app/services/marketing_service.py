# app/services/marketing_service.py

import os
import smtplib
import urllib.parse
import urllib.request
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.models.client import Client
from app.models.marketing_campaign import MarketingCampaign
from app.services.audit_service import AuditService


# ============================================================
# SMS ПРОВАЙДЕРЫ
# ============================================================

class BaseSMSProvider:
    """Базовый класс SMS-провайдера"""
    def send(self, phone: str, message: str) -> dict:
        raise NotImplementedError


class SMSCRuProvider(BaseSMSProvider):
    """SMSC.ru — популярный SMS-провайдер в РФ"""

    def __init__(self, login: str | None = None, password: str | None = None, sender: str | None = None):
        self.login = login or os.getenv("SMSC_LOGIN", "")
        self.password = password or os.getenv("SMSC_PASSWORD", "")
        self.sender = sender or os.getenv("SMSC_SENDER", "")
        self.enabled = bool(self.login and self.password)

    def send(self, phone: str, message: str) -> dict:
        if not self.enabled:
            return {"status": "mock", "provider": "smsc.ru", "phone": phone, "reason": "no_credentials"}

        # Нормализуем телефон
        phone = self._normalize_phone(phone)

        params = {
            "login": self.login,
            "psw": self.password,
            "phones": phone,
            "mes": message[:1000],  # smsc ограничение
            "sender": self.sender,
            "fmt": 3,  # JSON ответ
            "charset": "utf-8",
        }

        url = "https://smsc.ru/sys/send.php?" + urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = resp.read().decode("utf-8")
                return {"status": "sent", "provider": "smsc.ru", "phone": phone, "response": result}
        except Exception as e:
            return {"status": "error", "provider": "smsc.ru", "phone": phone, "error": str(e)}

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if not digits.startswith("7") and len(digits) == 10:
            digits = "7" + digits
        return digits


class MockSMSProvider(BaseSMSProvider):
    """Mock-провайдер для тестирования (логирует, не отправляет)"""

    def send(self, phone: str, message: str) -> dict:
        return {
            "status": "mock_delivered",
            "provider": "mock",
            "phone": phone,
            "message_preview": message[:50],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ============================================================
# EMAIL ПРОВАЙДЕР
# ============================================================

class EmailProvider:
    """SMTP-провайдер для email-рассылок"""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("SMTP_FROM", self.user)
        self.enabled = bool(self.host and self.user and self.password)

    def send(self, to_email: str, subject: str, body: str, html: bool = False) -> dict:
        if not self.enabled:
            return {"status": "mock", "provider": "smtp", "to": to_email, "reason": "no_smtp_config"}

        try:
            msg = f"From: {self.from_addr}\nTo: {to_email}\n"
            msg += f"Subject: {subject}\n"
            msg += f"Content-Type: text/{'html' if html else 'plain'}; charset=utf-8\n\n"
            msg += body

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to_email], msg.encode("utf-8"))

            return {"status": "sent", "provider": "smtp", "to": to_email}
        except Exception as e:
            return {"status": "error", "provider": "smtp", "to": to_email, "error": str(e)}


# ============================================================
# MARKETING SERVICE
# ============================================================

class MarketingService:
    """Сервис маркетинга: сегменты, кампании, SMS, email-рассылки"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

        # Инициализация провайдеров
        smsc_login = os.getenv("SMSC_LOGIN")
        smsc_pass = os.getenv("SMSC_PASSWORD")
        if smsc_login and smsc_pass:
            self.sms = SMSCRuProvider(smsc_login, smsc_pass)
        else:
            self.sms = MockSMSProvider()

        self.email = EmailProvider()

    # ============================================================
    # СЕГМЕНТЫ
    # ============================================================

    def get_segments(self) -> list[dict]:
        """Анализ сегментов клиентской базы"""
        now = datetime.now(timezone.utc)

        # Всего клиентов
        total = self.db.execute(select(func.count(Client.id))).scalar() or 0

        # Активные (есть посещение за 7 дней)
        from app.models.visit import Visit
        active_subq = (
            select(Visit.client_id)
            .where(Visit.entry_at >= now - timedelta(days=7))
            .distinct()
            .subquery()
        )
        active_count = self.db.execute(
            select(func.count(Client.id)).where(Client.id.in_(select(active_subq.c.client_id)))
        ).scalar() or 0

        # Новые (зарегистрированы за 7 дней)
        new_count = self.db.execute(
            select(func.count(Client.id))
            .where(Client.created_at >= now - timedelta(days=7))
        ).scalar() or 0

        # Спящие (не заходили 30+ дней)
        sleeping_subq = (
            select(Visit.client_id)
            .where(Visit.entry_at >= now - timedelta(days=30))
            .distinct()
            .subquery()
        )
        sleeping_count = self.db.execute(
            select(func.count(Client.id))
            .where(~Client.id.in_(select(sleeping_subq.c.client_id)))
            .where(Client.is_active == True)
        ).scalar() or 0

        # Отток (не заходили 60+ дней)
        churn_subq = (
            select(Visit.client_id)
            .where(Visit.entry_at >= now - timedelta(days=60))
            .distinct()
            .subquery()
        )
        churn_count = self.db.execute(
            select(func.count(Client.id))
            .where(~Client.id.in_(select(churn_subq.c.client_id)))
            .where(Client.is_active == True)
        ).scalar() or 0

        # По подпискам
        from app.models.subscription import Subscription
        active_subs = self.db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.status == "active")
        ).scalar() or 0
        frozen_subs = self.db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.status == "frozen")
        ).scalar() or 0

        return [
            {"id": "all", "name": "Все клиенты", "count": total, "description": "Полная база клиентов"},
            {"id": "new", "name": "Новые (7 дней)", "count": new_count, "description": "Недавно зарегистрированные"},
            {"id": "active", "name": "Активные (7 дней)", "count": active_count, "description": "Посещали за последние 7 дней"},
            {"id": "with_subscription", "name": "С абонементом", "count": active_subs, "description": "Активные абонементы"},
            {"id": "frozen", "name": "Замороженные", "count": frozen_subs, "description": "Приостановленные абонементы"},
            {"id": "sleeping", "name": "Спящие (30+ дней)", "count": sleeping_count, "description": "Не посещали 30+ дней"},
            {"id": "churn", "name": "Отток (60+ дней)", "count": churn_count, "description": "Не посещали 60+ дней — требуют внимания"},
            {"id": "birthday", "name": "Именинники", "count": self._get_birthday_count(), "description": "День рождения в этом месяце"},
        ]

    def _get_birthday_count(self) -> int:
        """Клиенты с днём рождения в текущем месяце"""
        from sqlalchemy import extract
        now = datetime.now(timezone.utc)
        return self.db.execute(
            select(func.count(Client.id))
            .where(extract("month", Client.birth_date) == now.month)
            .where(Client.is_active == True)
        ).scalar() or 0

    def get_segment_clients(self, segment_id: str, offset: int = 0, limit: int = 100) -> dict:
        """Получить клиентов сегмента"""
        now = datetime.now(timezone.utc)
        from app.models.visit import Visit

        query = select(Client).where(Client.is_active == True)

        if segment_id == "new":
            query = query.where(Client.created_at >= now - timedelta(days=7))
        elif segment_id == "active":
            active_subq = (
                select(Visit.client_id)
                .where(Visit.entry_at >= now - timedelta(days=7))
                .distinct()
                .subquery()
            )
            query = query.where(Client.id.in_(select(active_subq.c.client_id)))
        elif segment_id == "sleeping":
            recent_subq = (
                select(Visit.client_id)
                .where(Visit.entry_at >= now - timedelta(days=30))
                .distinct()
                .subquery()
            )
            query = query.where(~Client.id.in_(select(recent_subq.c.client_id)))
        elif segment_id == "churn":
            recent_subq = (
                select(Visit.client_id)
                .where(Visit.entry_at >= now - timedelta(days=60))
                .distinct()
                .subquery()
            )
            query = query.where(~Client.id.in_(select(recent_subq.c.client_id)))
        elif segment_id == "birthday":
            from sqlalchemy import extract
            query = query.where(extract("month", Client.birth_date) == now.month)

        query = query.order_by(Client.created_at.desc())
        clients = list(self.db.execute(query).scalars().all())
        paginated = clients[offset:offset + limit]

        return {
            "segment_id": segment_id,
            "total": len(clients),
            "items": [
                {
                    "id": str(c.id),
                    "name": f"{c.first_name} {c.last_name}",
                    "phone": c.phone,
                    "email": c.email,
                }
                for c in paginated
            ],
        }

    # ============================================================
    # SMS РАССЫЛКА
    # ============================================================

    def send_sms(
        self,
        phones: list[str],
        message: str,
        campaign_name: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> dict:
        """Отправить SMS на список номеров"""
        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")
        if len(message) > 1000:
            raise HTTPException(status_code=400, detail="Сообщение не может быть длиннее 1000 символов")

        results = []
        success = 0
        failed = 0
        mock = 0

        for phone in phones:
            result = self.sms.send(phone, message)
            results.append(result)
            if result["status"] in ("sent", "mock_delivered"):
                success += 1
            if result["status"] == "mock_delivered":
                mock += 1
            elif result["status"] == "error":
                failed += 1

        # Сохраняем в аудит
        campaign_id = str(uuid4()) if campaign_name else None
        self.audit.log(
            action="marketing.sms.send",
            status="success" if success > 0 else "error",
            actor_user_id=actor_user_id,
            message=f"SMS-рассылка '{campaign_name or 'без названия'}': {success}/{len(phones)} доставлено",
            after_data={
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "total_recipients": len(phones),
                "success": success,
                "failed": failed,
                "mock": mock,
            },
        )

        return {
            "status": "completed",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "total": len(phones),
            "success": success,
            "failed": failed,
            "mock_mode": mock > 0,
            "details": results[:10],  # Первые 10 для деталей
        }

    def send_sms_to_segment(
        self,
        segment_id: str,
        message: str,
        campaign_name: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> dict:
        """Отправить SMS сегменту клиентов"""
        segment_data = self.get_segment_clients(segment_id, limit=9999)
        phones = [c["phone"] for c in segment_data["items"] if c.get("phone")]

        if not phones:
            return {"status": "no_recipients", "segment": segment_id, "message": "В сегменте нет клиентов с телефоном"}

        return self.send_sms(phones, message, campaign_name, actor_user_id)

    # ============================================================
    # EMAIL РАССЫЛКА
    # ============================================================

    def send_email(
        self,
        to_emails: list[str],
        subject: str,
        body: str,
        html: bool = False,
        campaign_name: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> dict:
        """Отправить email-рассылку"""
        results = []
        success = 0

        for email in to_emails:
            result = self.email.send(email, subject, body, html)
            results.append(result)
            if result["status"] in ("sent", "mock"):
                success += 1

        self.audit.log(
            action="marketing.email.send",
            status="success" if success > 0 else "error",
            actor_user_id=actor_user_id,
            message=f"Email-рассылка '{campaign_name or 'без названия'}': {success}/{len(to_emails)}",
            after_data={
                "campaign_name": campaign_name,
                "total_recipients": len(to_emails),
                "success": success,
            },
        )

        return {
            "status": "completed",
            "total": len(to_emails),
            "success": success,
            "mock_mode": not self.email.enabled,
        }

    # ============================================================
    # КАМПАНИИ
    # ============================================================

    def list_campaigns(self, offset: int = 0, limit: int = 100) -> dict:
        """Список маркетинговых кампаний"""
        campaigns = self.db.execute(
            select(MarketingCampaign).order_by(MarketingCampaign.created_at.desc())
        ).scalars().all()

        return {
            "items": [self._serialize_campaign(c) for c in campaigns[offset:offset + limit]],
            "total": len(campaigns),
        }

    def create_campaign(self, data: dict, actor_user_id: UUID | None = None) -> dict:
        """Создать маркетинговую кампанию"""
        campaign = MarketingCampaign(
            id=uuid4(),
            name=data["name"],
            campaign_type=data.get("type", "sms"),
            channel=data.get("channel", "sms"),
            segment_id=data.get("segment_id"),
            message_template=data.get("message_template", ""),
            subject=data.get("subject", ""),
            scheduled_at=data.get("scheduled_at"),
            status="draft",
            created_by=actor_user_id,
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)

        self.audit.log(
            action="marketing.campaign.create",
            status="success",
            actor_user_id=actor_user_id,
            message=f"Создана кампания '{campaign.name}'",
            after_data={"campaign_id": str(campaign.id), "type": campaign.campaign_type},
        )

        return self._serialize_campaign(campaign)

    def launch_campaign(self, campaign_id: UUID, actor_user_id: UUID | None = None) -> dict:
        """Запустить кампанию"""
        campaign = self.db.execute(
            select(MarketingCampaign).where(MarketingCampaign.id == campaign_id)
        ).scalar_one_or_none()

        if not campaign:
            raise HTTPException(status_code=404, detail="Кампания не найдена")

        if campaign.status not in ("draft", "scheduled"):
            raise HTTPException(status_code=400, detail=f"Нельзя запустить кампанию в статусе '{campaign.status}'")

        # Получаем клиентов сегмента
        if campaign.segment_id:
            segment_data = self.get_segment_clients(campaign.segment_id, limit=9999)
        else:
            segment_data = {"items": [], "total": 0}

        result = {"campaign_id": str(campaign_id), "recipients": segment_data["total"]}

        if campaign.channel == "sms":
            phones = [c["phone"] for c in segment_data["items"] if c.get("phone")]
            if phones:
                sms_result = self.send_sms(
                    phones, campaign.message_template, campaign.name, actor_user_id
                )
                result["sms_result"] = sms_result
            else:
                result["warning"] = "Нет клиентов с телефоном в сегменте"

        elif campaign.channel == "email":
            emails = [c["email"] for c in segment_data["items"] if c.get("email")]
            if emails:
                email_result = self.send_email(
                    emails, campaign.subject, campaign.message_template,
                    campaign_name=campaign.name, actor_user_id=actor_user_id
                )
                result["email_result"] = email_result
            else:
                result["warning"] = "Нет клиентов с email в сегменте"

        campaign.status = "sent"
        campaign.sent_at = datetime.now(timezone.utc)
        self.db.commit()

        result["status"] = "launched"
        return result

    @staticmethod
    def _serialize_campaign(campaign) -> dict:
        return {
            "id": str(campaign.id),
            "name": campaign.name,
            "type": campaign.campaign_type,
            "channel": campaign.channel,
            "segment_id": campaign.segment_id,
            "status": campaign.status,
            "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
            "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        }
