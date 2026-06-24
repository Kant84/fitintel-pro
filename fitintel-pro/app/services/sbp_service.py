import uuid
import time
from typing import Optional


class SbpAndSubscriptionManager:
    """
    Универсальный менеджер СБП и рекуррентных платежей.
    Режим mock=True — для тестирования без реального банка.
    """

    def __init__(self, mock: bool = True, terminal_key: str = "", password: str = ""):
        self.mock = mock
        self.terminal_key = terminal_key
        self.password = password
        self._pending: dict = {}  # order_id -> {status, amount}

    def generate_dynamic_qr(self, amount: float, order_id: str) -> dict:
        """
        Возвращает dict:
        {
            "qr_url": "https://...",
            "payment_id": "..."
        }
        """
        if self.mock:
            self._pending[order_id] = {"status": "pending", "amount": amount}
            return {
                "qr_url": f"https://pay.example.com/sbp?order={order_id}&amount={int(amount * 100)}",
                "payment_id": order_id
            }

        # TODO: Реальная интеграция Т-Банк / Сбер
        # 1. POST /v2/Init -> получить PaymentId
        # 2. POST /v2/GetQr -> получить QR URL
        raise NotImplementedError("Реальный СБП требует настройки мерчанта")

    def check_qr_payment_status(self, order_id: str) -> bool:
        """True = клиент оплатил."""
        if self.mock:
            if order_id in self._pending:
                # Имитация задержки
                time.sleep(1)
                self._pending[order_id]["status"] = "completed"
                return True
            return False

        # TODO: Реальный запрос к банку
        # GET /v2/GetState?PaymentId={order_id}
        raise NotImplementedError

    def register_autopay_token(self, client_id: int) -> str:
        """
        Привязка карты для рекуррентов.
        Возвращает RebillId. Карту в БД не храним — только токен!
        """
        if self.mock:
            return f"token_card_{uuid.uuid4().hex[:12]}_client{client_id}"

        # TODO: После первой оплаты с Recurrent=1 банк возвращает RebillId
        raise NotImplementedError

    def charge_subscription(self, amount: float, rebill_id: str) -> dict:
        """Рекуррентное списание по токену."""
        if self.mock:
            print(f"[RECURRENT] Списание {amount} руб по токену {rebill_id} — УСПЕШНО")
            return {"success": True, "amount": amount, "rebill_id": rebill_id}

        # TODO: POST /v2/Charge (Т-Банк) или аналог Сбера
        raise NotImplementedError