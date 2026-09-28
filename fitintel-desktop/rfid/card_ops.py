import urllib.request
from rfid.constants import KEY_B_ITC, EMPTY_CARD

try:
    from rfid.direct_reader import DirectReader
    _DIRECT = DirectReader()
except Exception:
    _DIRECT = None


class _ReaderShim:
    """/reader/* — напрямую к USB; всё остальное — через tab._req (сервер)."""
    def __init__(self, tab_req):
        self._tab_req = tab_req

    def __call__(self, method, path, data=None):
        data = data or {}
        if _DIRECT is not None and path.startswith("/reader/"):
            return self._local(path, data)
        return self._tab_req(method, path, data)

    def _local(self, path, data):
        if path == "/reader/status":
            return _DIRECT.status()
        if path == "/reader/detect-card":
            uid = _DIRECT.detect_uid()
            return {"uid": uid} if uid else {"_err": "no card"}
        if path == "/reader/read-sector":
            blocks = _DIRECT.read_sector(data.get("sector", 0),
                                         data.get("key_type", "B"),
                                         data.get("key_hex", KEY_B_ITC))
            return {"blocks": blocks} if blocks else {"_err": "read failed"}
        if path == "/reader/write":
            ok = _DIRECT.write_block(data.get("sector", 0),
                                     data.get("block", 1),
                                     data.get("key_type", "B"),
                                     data.get("key_hex", KEY_B_ITC),
                                     data.get("data_hex", ""))
            return {"ok": True} if ok else {"_err": "write failed"}
        return {"_err": "unknown reader endpoint"}

class RFIDCardOps:
    def __init__(self, tab):
        self.tab = tab
        self._req = _ReaderShim(tab._req)
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