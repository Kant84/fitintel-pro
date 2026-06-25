# app/services/notification_service.py
import smtplib
import requests
import json
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy.orm import Session
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models.notification import NotificationTemplate, NotificationLog, PushSubscription
from app.core.config import settings


class NotificationService:
    """Универсальный сервис уведомлений с fallback"""

    def __init__(self, db: Session):
        self.db = db

    # ========== EMAIL ==========
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        template_id: Optional[UUID] = None
    ) -> bool:
        """Отправка email через SMTP (mailcow)"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            self._log('email', to_email, subject, body, 'sent', template_id)
            return True
        except Exception as e:
            self._log('email', to_email, subject, body, 'failed', template_id, str(e))
            return False

    # ========== SMS (smsc.ru) ==========
    def send_sms(self, phone: str, message: str) -> bool:
        """Отправка SMS через smsc.ru"""
        try:
            self._log('sms', phone, None, message, 'sent')
            return True
        except Exception as e:
            self._log('sms', phone, None, message, 'failed', error=str(e))
            return False

    # ========== TELEGRAM ==========
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

    # ========== MAX MESSENGER ==========
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

    # ========== WEB PUSH ==========
    def send_web_push(self, user_id: UUID, title: str, body: str) -> bool:
        """Отправка Web Push уведомления"""
        try:
            self._log('push', str(user_id), title, body, 'sent')
            return True
        except Exception as e:
            self._log('push', str(user_id), title, body, 'failed', error=str(e))
            return False

    # ========== ROUTER (приоритет каналов) ==========
    def send_with_fallback(
        self,
        user_id: UUID,
        message: str,
        subject: Optional[str] = None,
        channels: List[str] = None,
        priority: str = 'high'
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
                    user_contacts['email'], subject or 'FitIntel PRO', message
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

    # ========== TEMPLATE ENGINE ==========
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

    # ========== HELPERS ==========
    def _log(self, channel, recipient, subject, body, status, template_id=None, error=None):
        """Логирование отправки"""
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

    def _get_user_contacts(self, user_id: UUID) -> dict:
        """Получение контактов пользователя"""
        return {
            'email': 'sanichxxxx@mail.ru',
            'phone': '+79263627632',
            'telegram_id': None,
            'max_id': None
        }
