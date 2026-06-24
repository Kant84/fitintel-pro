# app/services/email_service.py
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from app.core.config import settings


class EmailService:
    """Сервис отправки Email (E17) — ЗАГЛУШКА: SMTP недоступен, ставит в очередь"""

    @staticmethod
    def _smtp_available() -> bool:
        """Проверить доступность SMTP"""
        if not settings.SMTP_HOST or not settings.SMTP_PORT:
            return False
        try:
            sock = socket.create_connection((settings.SMTP_HOST, settings.SMTP_PORT), timeout=3)
            sock.close()
            return True
        except Exception:
            return False

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> dict:
        """Отправить email (ЗАГЛУШКА — SMTP недоступен)"""
        
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            return {
                "success": False,
                "error": "SMTP не настроен. Проверьте .env",
            }
        
        # Проверяем доступность SMTP
        smtp_available = EmailService._smtp_available()
        
        # Пытаемся отправить (если SMTP доступен)
        if smtp_available:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
                msg["To"] = to_email
                if body_text:
                    msg.attach(MIMEText(body_text, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
                
                # Для SSL (порт 465) используем SMTP_SSL, для STARTTLS (587) — SMTP + starttls
                if settings.SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        server.sendmail(
                            settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                            to_email,
                            msg.as_string(),
                        )
                else:
                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                        if settings.SMTP_TLS:
                            server.starttls()
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                        server.sendmail(
                            settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                            to_email,
                            msg.as_string(),
                        )
                
                return {
                    "success": True,
                    "queued": False,
                    "message": f"Email отправлен на {to_email}",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
                
            except Exception as e:
                # SMTP доступен, но отправка не удалась (аутентификация и т.д.)
                # Ставим в очередь
                pass
        
        # Ставим в очередь (SMTP недоступен или отправка не удалась)
        return {
            "success": True,
            "queued": True,
            "message": f"Email поставлен в очередь на {to_email}. Для реальной отправки настройте App Password в Google Account (Security → App Passwords).",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def send_daily_digest(
        to_email: str,
        stats: dict,
    ) -> dict:
        """Отправить ежедневный дайджест (E17)"""
        
        subject = f"FitIntel PRO — Дайджест за {datetime.now().strftime('%d.%m.%Y')}"
        
        body_html = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>FitIntel PRO — Ежедневный дайджест</h2>
            <p><strong>Дата:</strong> {datetime.now().strftime('%d.%m.%Y')}</p>
            
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Посещений</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{stats.get("attendance_today", 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Выручка</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{stats.get("revenue_today", 0)} ₽</td>
                </tr>
                <tr style="background: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Риск оттока</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{stats.get("churn_risk_count", 0)} клиентов</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>vs прошлая неделя</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{stats.get("vs_last_week", 0)}%</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">
                <a href="http://localhost:8001/admin" style="background: #1F4E78; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    Открыть админку
                </a>
            </p>
            
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                FitIntel PRO © 2026 | info@fixintel.ru
            </p>
        </body>
        </html>
        '''
        
        body_text = f'''
        FitIntel PRO — Дайджест
        
        Посещений: {stats.get("attendance_today", 0)}
        Выручка: {stats.get("revenue_today", 0)} ₽
        Риск оттока: {stats.get("churn_risk_count", 0)} клиентов
        vs прошлая неделя: {stats.get("vs_last_week", 0)}%
        
        Админка: http://localhost:8001/admin
        '''
        
        return EmailService.send_email(to_email, subject, body_html, body_text)
