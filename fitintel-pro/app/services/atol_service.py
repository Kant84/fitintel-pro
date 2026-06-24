import uuid
import time
import requests
from typing import List, Dict, Optional


class AtolService:
    """
    Сервис для работы с онлайн-кассой АТОЛ через ДТО 10 (JSON API).
    URL по умолчанию: http://127.0.0.1:16732/requests
    """

    def __init__(self, base_url: str = "http://127.0.0.1:16732"):
        self.base_url = base_url.rstrip("/")
        self.requests_url = f"{self.base_url}/requests"
        # Если ДТО 10 требует Basic Auth, укажите здесь:
        self.auth = None  # пример: ("admin", "password")

    def _send_command(self, command_type: str, payload_data: dict, operator_name: str = "Админ") -> dict:
        """Отправка команды в АТОЛ с автоматическим polling-ом результата."""
        task_uuid = str(uuid.uuid4())
        request_payload = {
            "uuid": task_uuid,
            "request": {
                "type": command_type,
                "operator": {"name": operator_name},
                **payload_data
            }
        }

        try:
            resp = requests.post(
                self.requests_url,
                json=request_payload,
                auth=self.auth,
                timeout=10
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "АТОЛ недоступен. Проверьте эмулятор/драйвер."}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Таймаут соединения с АТОЛ."}

        # АТОЛ обрабатывает команды асинхронно — опрашиваем результат
        return self._wait_result(task_uuid)

    def _wait_result(self, task_uuid: str, max_attempts: int = 10, delay: float = 0.5) -> dict:
        """Опрос результата выполнения задачи по UUID."""
        result_url = f"{self.base_url}/results/{task_uuid}"
        alt_url = f"{self.requests_url}/{task_uuid}"

        for _ in range(max_attempts):
            time.sleep(delay)
            try:
                r = requests.get(result_url, auth=self.auth, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "ready" or "result" in data:
                        return {"success": True, "data": data}
                    if data.get("status") == "error":
                        return {"success": False, "error": data.get("error", "Ошибка АТОЛ")}

                # Альтернативный endpoint для некоторых версий ДТО
                r2 = requests.get(alt_url, auth=self.auth, timeout=5)
                if r2.status_code == 200:
                    d2 = r2.json()
                    if d2.get("status") == "ready":
                        return {"success": True, "data": d2}
            except Exception:
                continue

        return {"success": False, "error": "АТОЛ не ответил за отведенное время"}

    def open_shift(self, operator_name: str = "Админ") -> dict:
        """Открыть смену на кассе."""
        return self._send_command("openShift", {}, operator_name)

    def print_sale_check(
        self,
        items: List[dict],
        payment_type: str = "electronically",
        total: Optional[float] = None,
        slip: str = ""
    ) -> dict:
        """
        Пробить чек прихода.
        payment_type: 'cash' (наличные), 'electronically' (электронно), 'prepaid' (предоплата)
        """
        if total is None:
            total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)

        # Маппинг типов оплаты для АТОЛ
        pt_map = {"cash": 0, "electronically": 1, "prepaid": 2}
        pt_code = pt_map.get(payment_type, 1)

        receipt_payload = {
            "receipt": {
                "items": items,
                "payments": [{"type": pt_code, "sum": total}],
            }
        }
        if slip:
            receipt_payload["receipt"]["additionalReceiptInfo"] = slip

        return self._send_command("sell", receipt_payload)

    def print_z_report(self, operator_name: str = "Админ") -> dict:
        """Закрыть смену (Z-отчет)."""
        return self._send_command("closeShift", {}, operator_name)

    def cancel_last_operation(self) -> dict:
        """Отменить последнюю операцию."""
        return self._send_command("cancel", {})