import urllib.request
from rfid.constants import KEY_B_ITC, EMPTY_CARD


class RFIDCardOps:
    def __init__(self, tab):
        self.tab = tab
        self._req = tab._req
        self._log = tab._log

    def reset_card(self, uid):
        """Очистка карты (блок 1) + отвязка от клиента. Трейлер НЕ трогаем — карта остаётся рабочей."""
        # Только очистка блока 1 (ключ B) — убираем данные клиента с карты
        r1 = self._req("POST", "/reader/write", {
            "sector": 0, "block": 1, "key_type": "B",
            "key_hex": KEY_B_ITC, "data_hex": EMPTY_CARD})
        if isinstance(r1, dict) and "_err" not in r1:
            self._log(self.tab.log, "✅ Блок 1 очищен (данные клиента удалены)")
        else:
            self._log(self.tab.log, "ℹ️ Блок 1 недоступен")
        # Трейлер НЕ сбрасываем — карта остаётся с рабочим ключом B

    def encode_card(self):
        """Очистка носителя (с fallback на ключ A)."""
        self._log(self.tab.log, "🔷 Поднесите носитель для очистки...")

        r = self._req("POST", "/reader/detect-card")
        if isinstance(r, dict) and "_err" in r:
            self._log(self.tab.log, "❌ Носитель не обнаружен")
            return

        # Пробуем ключ B
        r2 = self._req("POST", "/reader/write", {
            "sector": 0, "block": 1, "key_type": "B",
            "key_hex": KEY_B_ITC, "data_hex": EMPTY_CARD})

        # Fallback: ключ A для factory default карт
        if isinstance(r2, dict) and "_err" in r2:
            self._log(self.tab.log, "⚠️ Ключ B не подходит, пробуем ключ A...")
            r2 = self._req("POST", "/reader/write", {
                "sector": 0, "block": 1, "key_type": "A",
                "key_hex": "FFFFFFFFFFFF", "data_hex": EMPTY_CARD})

        if isinstance(r2, dict) and "_err" not in r2:
            self._log(self.tab.log, "✅ Носитель очищен. Клиент сохранён.")
        else:
            self._log(self.tab.log, "❌ Ошибка: " + str(r2.get("_body", str(r2))))