# app/services/telegram_bot_service.py
"""
Telegram Bot для FitIntel Pro.
Уведомления, баланс, QR-код, расписание, заморозка.
"""

import os
import urllib.request
import urllib.parse
import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.client import Client
from app.models.visit import Visit
from app.models.subscription import Subscription
from app.models.wallet import Wallet
from app.models.credential import Credential


TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramBotService:
    """Telegram Bot — уведомления и команды для клиентов"""

    def __init__(self, db: Session):
        self.db = db
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.enabled = bool(self.token)
        self.api_base = TELEGRAM_API.format(token=self.token) if self.token else ""

    def _api(self, method: str, params: dict = None) -> dict:
        """Вызов Telegram Bot API"""
        if not self.enabled:
            return {"ok": False, "description": "Bot token not configured"}
        url = f"{self.api_base}/{method}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ============================================================
    # ОТПРАВКА СООБЩЕНИЙ
    # ============================================================

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> dict:
        """Отправить текстовое сообщение"""
        return self._api("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })

    def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> dict:
        """Отправить фото"""
        return self._api("sendPhoto", {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        })

    # ============================================================
    # УВЕДОМЛЕНИЯ
    # ============================================================

    def notify_visit_entry(self, client_id: str, chat_id: str) -> dict:
        """Уведомление о входе в клуб"""
        client = self.db.execute(select(Client).where(Client.id == client_id)).scalar_one_or_none()
        if not client:
            return {"ok": False}
        now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
        text = (
            f"<b>✅ Добро пожаловать, {client.first_name}!</b>\n\n"
            f"Вы вошли в клуб в {now}.\n"
            f"Приятной тренировки! 💪"
        )
        return self.send_message(chat_id, text)

    def notify_visit_exit(self, client_id: str, chat_id: str, duration_min: int) -> dict:
        """Уведомление о выходе из клуба"""
        client = self.db.execute(select(Client).where(Client.id == client_id)).scalar_one_or_none()
        if not client:
            return {"ok": False}
        text = (
            f"<b>👋 До свидания, {client.first_name}!</b>\n\n"
            f"Длительность тренировки: <b>{duration_min} мин</b>\n"
            f"Отличная работа! 🔥"
        )
        return self.send_message(chat_id, text)

    def notify_subscription_expiring(self, client_id: str, chat_id: str, days_left: int) -> dict:
        """Уведомление об истечении абонемента"""
        text = (
            f"<b>⏰ Напоминание</b>\n\n"
            f"Ваш абонемент истекает через <b>{days_left} дней</b>.\n"
            f"Не забудьте продлить! 💳"
        )
        return self.send_message(chat_id, text)

    def notify_payment_success(self, client_id: str, chat_id: str, amount: float, service: str) -> dict:
        """Уведомление об успешной оплате"""
        text = (
            f"<b>✅ Оплата успешна</b>\n\n"
            f"Сумма: <b>{amount:.2f} ₽</b>\n"
            f"Услуга: {service}\n\n"
            f"Спасибо за оплату! 🎉"
        )
        return self.send_message(chat_id, text)

    # ============================================================
    # КОМАНДЫ БОТА
    # ============================================================

    def handle_command(self, chat_id: str, command: str, client_id: str | None = None) -> dict:
        """Обработка команд бота"""
        cmd = command.lower().strip()

        if cmd == "/start":
            return self.send_message(chat_id, self._welcome_text())

        elif cmd == "/help":
            return self.send_message(chat_id, self._help_text())

        elif cmd == "/balance":
            if not client_id:
                return self.send_message(chat_id, "Привяжите аккаунт с помощью /link <код>")
            return self._cmd_balance(chat_id, client_id)

        elif cmd == "/qrcode":
            if not client_id:
                return self.send_message(chat_id, "Привяжите аккаунт с помощью /link <код>")
            return self._cmd_qrcode(chat_id, client_id)

        elif cmd == "/subscriptions":
            if not client_id:
                return self.send_message(chat_id, "Привяжите аккаунт с помощью /link <код>")
            return self._cmd_subscriptions(chat_id, client_id)

        elif cmd == "/freeze":
            if not client_id:
                return self.send_message(chat_id, "Привяжите аккаунт с помощью /link <код>")
            return self.send_message(chat_id, "Для заморозки абонемента посетите рецепцию или личный кабинет.")

        elif cmd == "/visits":
            if not client_id:
                return self.send_message(chat_id, "Привяжите аккаунт с помощью /link <код>")
            return self._cmd_visits(chat_id, client_id)

        else:
            return self.send_message(chat_id, "Неизвестная команда. Используйте /help")

    def _welcome_text(self) -> str:
        return (
            "<b>🤖 FitIntel Pro Bot</b>\n\n"
            "Ваш персональный помощник в фитнес-клубе!\n\n"
            "<b>Команды:</b>\n"
            "/balance — Баланс и транзакции\n"
            "/qrcode — Мой QR-пропуск\n"
            "/subscriptions — Мои абонементы\n"
            "/visits — История посещений\n"
            "/freeze — Заморозка абонемента\n"
            "/help — Справка\n\n"
            "Привяжите аккаунт: /link <ваш-код>"
        )

    def _help_text(self) -> str:
        return (
            "<b>📖 Справка по командам</b>\n\n"
            "/start — Начать работу\n"
            "/balance — Проверить баланс кошелька\n"
            "/qrcode — Получить QR-код для прохода\n"
            "/subscriptions — Список активных абонементов\n"
            "/visits — История посещений за месяц\n"
            "/freeze — Информация о заморозке\n"
            "/help — Эта справка\n\n"
            "<b>Поддержка:</b> +7 (495) 123-45-67"
        )

    def _cmd_balance(self, chat_id: str, client_id: str) -> dict:
        """Команда /balance"""
        wallet = self.db.execute(select(Wallet).where(Wallet.client_id == client_id)).scalar_one_or_none()
        if not wallet:
            return self.send_message(chat_id, "Кошелёк не найден.")
        text = (
            f"<b>💰 Ваш баланс</b>\n\n"
            f"Доступно: <b>{wallet.balance:.2f} ₽</b>\n\n"
            f"Пополнить: fitintel.pro/pay"
        )
        return self.send_message(chat_id, text)

    def _cmd_qrcode(self, chat_id: str, client_id: str) -> dict:
        """Команда /qrcode — отправляет ссылку на QR"""
        credential = self.db.execute(
            select(Credential)
            .where(Credential.client_id == client_id)
            .where(Credential.is_active == True)
            .where(Credential.is_blocked == False)
        ).scalars().first()

        if not credential:
            return self.send_message(chat_id, "QR-код не найден. Получите его в личном кабинете.")

        text = f"<b>📱 Ваш QR-пропуск</b>\n\nКод: <code>{credential.code}</code>\n\nПокажите на турникете!"
        return self.send_message(chat_id, text)

    def _cmd_subscriptions(self, chat_id: str, client_id: str) -> dict:
        """Команда /subscriptions"""
        subs = self.db.execute(
            select(Subscription)
            .where(Subscription.client_id == client_id)
            .where(Subscription.status.in_(["active", "frozen"]))
        ).scalars().all()

        if not subs:
            return self.send_message(chat_id, "У вас нет активных абонементов.")

        text = "<b>🎫 Ваши абонементы</b>\n\n"
        for s in subs:
            status_emoji = "✅" if s.status == "active" else "❄️"
            end = s.end_date.strftime("%d.%m.%Y") if s.end_date else "N/A"
            text += f"{status_emoji} {s.tariff_name or 'Абонемент'} — до {end}\n"

        return self.send_message(chat_id, text)

    def _cmd_visits(self, chat_id: str, client_id: str) -> dict:
        """Команда /visits"""
        visits = self.db.execute(
            select(Visit)
            .where(Visit.client_id == client_id)
            .order_by(Visit.entry_at.desc())
            .limit(10)
        ).scalars().all()

        if not visits:
            return self.send_message(chat_id, "История посещений пуста.")

        text = "<b>📊 Последние посещения</b>\n\n"
        for v in visits:
            entry = v.entry_at.strftime("%d.%m %H:%M") if v.entry_at else "?"
            duration = ""
            if v.duration_minutes:
                duration = f" ({v.duration_minutes} мин)"
            text += f"• {entry}{duration}\n"

        return self.send_message(chat_id, text)

    # ============================================================
    # WEBHOOK
    # ============================================================

    def setup_webhook(self, webhook_url: str) -> dict:
        """Установить webhook для получения обновлений"""
        return self._api("setWebhook", {"url": webhook_url})

    def delete_webhook(self) -> dict:
        """Удалить webhook"""
        return self._api("deleteWebhook")

    def get_webhook_info(self) -> dict:
        """Информация о webhook"""
        return self._api("getWebhookInfo")

    def process_webhook_update(self, update: dict) -> dict:
        """Обработать входящее обновление от Telegram"""
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        # TODO: связать chat_id с client_id через таблицу telegram_bindings
        return self.handle_command(chat_id, text)
