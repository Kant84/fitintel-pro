import sys, json, urllib.request, time, os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

API_BASE = "http://127.0.0.1:8001/api/v1"
KEY_B_ITC = "666666666666"
CACHE_FILE = "rfid_uid_cache.json"

_GLOBAL_TOKEN = None


def set_global_token(tok):
    global _GLOBAL_TOKEN
    _GLOBAL_TOKEN = tok


def api_post(endpoint, payload):
    try:
        headers = {"Content-Type": "application/json"}
        if _GLOBAL_TOKEN:
            headers["Authorization"] = "Bearer " + _GLOBAL_TOKEN
        req = urllib.request.Request(
            API_BASE + endpoint,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_err": str(e)}


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class RFIDMonitorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(400, 260)
        self.setStyleSheet("background-color: #0f172a; color: #e2e8f0; border-radius: 12px; border: 2px solid #334155;")
        self._last_uid = None
        self._build_ui()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(500)
        self.hide()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        lay.setContentsMargins(14, 12, 14, 12)

        self.header = QLabel("🔷  RFID Монитор")
        self.header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.header.setStyleSheet("color: #38bdf8;")
        lay.addWidget(self.header)

        self.lbl_uid = QLabel("UID: —")
        self.lbl_uid.setFont(QFont("Consolas", 12))
        self.lbl_uid.setStyleSheet("color: #f59e0b;")
        lay.addWidget(self.lbl_uid)

        self.lbl_sector = QLabel("Сектор: —")
        self.lbl_sector.setFont(QFont("Segoe UI", 12))
        self.lbl_sector.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.lbl_sector)

        self.lbl_type = QLabel("Тип карты: —")
        self.lbl_type.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_type.setStyleSheet("color: #10b981;")
        lay.addWidget(self.lbl_type)

        self.lbl_locker = QLabel("Шкафчик: —")
        self.lbl_locker.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_locker.setStyleSheet("color: #f472b6;")
        lay.addWidget(self.lbl_locker)

        self.lbl_client = QLabel("Клиент: —")
        self.lbl_client.setFont(QFont("Segoe UI", 12))
        self.lbl_client.setStyleSheet("color: #e2e8f0;")
        lay.addWidget(self.lbl_client)

        self.lbl_raw = QLabel("")
        self.lbl_raw.setFont(QFont("Consolas", 9))
        self.lbl_raw.setStyleSheet("color: #475569;")
        self.lbl_raw.setWordWrap(True)
        lay.addWidget(self.lbl_raw)

    def _poll(self):
        det = api_post("/reader/detect-card", {})
        uid = det.get("uid") if "_err" not in det else None
        if uid:
            if uid != self._last_uid:
                self._last_uid = uid
                self._show_card(uid)
        else:
            if self._last_uid is not None:
                self._last_uid = None
                self.hide()

    def clear_client(self):
        """Вызывается при отвязке клиента. Очищает кэш и сбрасывает состояние."""
        # Удаляем из локального кэша
        if self._last_uid:
            try:
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                    if self._last_uid.upper() in cache:
                        del cache[self._last_uid.upper()]
                        with open(CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        # Сбрасываем состояние — при следующем poll карта перечитается
        self._last_uid = None
        self.hide()

    def refresh_card(self):
        """Вызывается при привязке клиента. Сбрасывает _last_uid, чтобы сразу перечитать карту."""
        self._last_uid = None
        # Не скрываем — при следующем poll покажет обновлённые данные

    def _show_card(self, uid):
        r = api_post("/reader/read-sector", {
            "sector": 0,
            "key_type": "B",
            "key_hex": KEY_B_ITC
        })
        block1 = ""
        card_type = "—"
        locker_num = None
        sector = 0
        if "_err" not in r and "blocks" in r:
            blocks = r.get("blocks", {})
            block1 = blocks.get("block_1", "")
            card_type, locker_num = self._parse(block1)
        else:
            card_type = "Неизвестный формат"

        # Ищем клиента в локальном кэше
        cache = _load_cache()
        client_name = cache.get(uid.upper())

        # Fallback: пробуем /rfid/scan
        if not client_name:
            scan = api_post("/rfid/scan", {"card_uid": uid, "device_id": "ACS-ACR1252-001"})
            if "_err" not in scan and scan.get("found"):
                client_name = scan.get("full_name", "")

        self.lbl_uid.setText("UID: " + uid)
        self.lbl_sector.setText("Сектор: " + str(sector))
        self.lbl_type.setText("Тип карты: " + card_type)

        if locker_num:
            self.lbl_locker.setText("🔒 Шкафчик №" + str(locker_num))
            self.lbl_locker.setStyleSheet("color: #f472b6;")
        else:
            self.lbl_locker.setText("🔓 Шкафчик не назначен")
            self.lbl_locker.setStyleSheet("color: #64748b;")

        if client_name:
            self.lbl_client.setText("Клиент: " + client_name)
            self.lbl_client.setStyleSheet("color: #10b981;")
        else:
            self.lbl_client.setText("Клиент: Неизвестный")
            self.lbl_client.setStyleSheet("color: #ef4444;")

        self.lbl_raw.setText("block_1: " + block1)

        screen = self.screen().geometry()
        self.move(screen.width() - 420, screen.height() - 300)
        self.show()
        self.raise_()

    def _parse(self, b1: str):
        b1 = b1.strip().upper()

        if len(b1) < 12:
            return "Неизвестный формат", None

        if all(c == "0" for c in b1):
            return "Пустая карта", None

        if b1 == "025D000000000000000000000000005F":
            return "Пустая карта", None
        if b1 == "02000000000000000000000001000003":
            return "Карта администратора", None
        if b1 == "02000000000000000000000000000003":
            return "Карта доступа", None

        prefix = b1[:4]

        if prefix == "020B":
            b5 = b1[10:12] if len(b1) >= 12 else "00"
            try:
                n5 = int(b5, 16)
                if n5 > 0:
                    return "Номер шкафчика " + str(n5), n5
            except Exception:
                pass
            return "Номер шкафчика", None

        if prefix in ("0201", "0202"):
            b6 = b1[12:14] if len(b1) >= 14 else "00"
            try:
                n6 = int(b6, 16)
                if n6 > 0:
                    return "Карта клиента", n6
            except Exception:
                pass

            tail = b1[14:] if len(b1) >= 32 else b1[14:]
            is_all_zero = all(c == "0" for c in tail)
            ends_with_03 = tail.endswith("03")

            if is_all_zero or ends_with_03:
                if prefix == "0201":
                    return "Индивидуальный режим", None
                else:
                    return "Режим удаления", None

            return "Неизвестный формат", None

        if prefix == "0203":
            b6 = b1[12:14] if len(b1) >= 14 else "00"
            try:
                n6 = int(b6, 16)
                if n6 > 0:
                    return "Сброс замка, шкафчик №" + str(n6), n6
            except Exception:
                pass
            return "Сброс замка", None

        if prefix == "0200":
            if len(b1) >= 32:
                tail = b1[16:]
                bytes_tail = [tail[i:i+2] for i in range(0, len(tail), 2)]

                if all(b == "00" for b in bytes_tail):
                    return "Сервисная карта", None

                b11 = b1[22:24] if len(b1) >= 24 else "00"
                b14 = b1[28:30] if len(b1) >= 30 else "00"
                b15 = b1[30:32] if len(b1) >= 32 else "00"
                if b11 == "01" and b14 == "00" and b15 != "03":
                    return "Не обслуживается", None

                return "Карта администратора", None

            return "Сервисная карта", None

        for i in range(5, 11):
            s = i * 2
            e = s + 2
            if len(b1) >= e:
                try:
                    v = int(b1[s:e], 16)
                    if v > 0:
                        return "Карта клиента", v
                except Exception:
                    pass

        return "Неизвестный формат", None