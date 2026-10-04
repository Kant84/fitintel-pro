# -*- coding: utf-8 -*-
"""RFID Монитор — прямой доступ к считывателю (pyscard), опрос в потоке.
Появляется при карте, прячется без карты. Drag, позиция запоминается."""
import json, os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

KEY_B_ITC = "666666666666"
CACHE_FILE = "rfid_uid_cache.json"
POS_FILE = "rfid_widget_pos.json"

_GLOBAL_TOKEN = None


def set_global_token(tok):
    global _GLOBAL_TOKEN
    _GLOBAL_TOKEN = tok


def _api_base():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        return (cfg.get("api_base") or "http://localhost:8001/api/v1").rstrip("/")
    except Exception:
        return "http://localhost:8001/api/v1"


def api_post(endpoint, payload, timeout=3):
    try:
        headers = {"Content-Type": "application/json"}
        if _GLOBAL_TOKEN:
            headers["Authorization"] = "Bearer " + _GLOBAL_TOKEN
        req = urllib.request.Request(
            _api_base() + endpoint,
            data=json.dumps(payload).encode(),
            headers=headers, method="POST")
        import urllib.request as _u
        with _u.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_err": str(e)}


def api_get(endpoint, timeout=3):
    try:
        headers = {}
        if _GLOBAL_TOKEN:
            headers["Authorization"] = "Bearer " + _GLOBAL_TOKEN
        import urllib.request as _u
        with _u.urlopen(_u.Request(_api_base() + endpoint, headers=headers),
                        timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_err": str(e)}


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {}


class PollThread(QThread):
    """Опрос считывателя в фоне — GUI не фризит."""
    card = pyqtSignal(dict)   # {"uid":...} — карта; {} — сняли

    def run(self):
        try:
            from rfid.direct_reader import DirectReader
        except Exception:
            return
        rd = DirectReader()
        last = None
        while not self.isInterruptionRequested():
            uid = rd.detect_uid()
            if uid != last:
                last = uid
                if uid:
                    info = {"uid": uid}
                    blocks = rd.read_sector(0, "B", KEY_B_ITC)
                    info["block1"] = blocks.get("block_1", "")
                    name = _load_cache().get(uid.upper())
                    if not name:
                        scan = api_post("/rfid/scan",
                                        {"card_uid": uid, "device_id": "ACS-ACR1252-001"})
                        if "_err" not in scan and scan.get("found"):
                            name = scan.get("full_name", "")
                    info["client"] = name
                    # Статус аренды шкафчика (Rental) по UID
                    rental = api_get(f"/credentials/locker-privilege/by-uid/{uid}")
                    if "_err" not in rental and rental.get("has_privilege"):
                        info["rental"] = rental.get("valid_until") or "бессрочно"
                    else:
                        info["rental"] = None
                    self.card.emit(info)
                else:
                    self.card.emit({})
            self.msleep(1000)


class RFIDMonitorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(400, 290)
        self.setStyleSheet(
            "background-color: #0f172a; color: #e2e8f0;"
            " border-radius: 12px; border: 2px solid #334155;")
        self._drag_pos = None
        self._build_ui()
        self._thread = PollThread(self)
        self._thread.card.connect(self._on_card)
        self._thread.start()
        self.hide()

    def closeEvent(self, ev):
        self._thread.requestInterruption()
        self._thread.wait(2000)
        super().closeEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if (ev.buttons() & Qt.MouseButton.LeftButton
                and self._drag_pos is not None):
            self.move(ev.globalPosition().toPoint() - self._drag_pos)
            try:
                with open(POS_FILE, "w", encoding="utf-8") as f:
                    json.dump({"x": self.x(), "y": self.y()}, f)
            except Exception:
                pass
        super().mouseMoveEvent(ev)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        lay.setContentsMargins(14, 12, 14, 12)

        self.header = QLabel("🔷  RFID Монитор  (перетащите мышкой)")
        self.header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.header.setStyleSheet("color: #38bdf8;")
        lay.addWidget(self.header)

        self.lbl_uid = QLabel("UID: —")
        self.lbl_uid.setFont(QFont("Consolas", 12))
        self.lbl_uid.setStyleSheet("color: #f59e0b;")
        lay.addWidget(self.lbl_uid)

        self.lbl_sector = QLabel("Сектор: 0")
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

        self.lbl_rental = QLabel("Аренда шкафчика: —")
        self.lbl_rental.setFont(QFont("Segoe UI", 12))
        self.lbl_rental.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.lbl_rental)

        self.lbl_raw = QLabel("")
        self.lbl_raw.setFont(QFont("Consolas", 9))
        self.lbl_raw.setStyleSheet("color: #475569;")
        self.lbl_raw.setWordWrap(True)
        lay.addWidget(self.lbl_raw)

    def _on_card(self, info: dict):
        if not info:
            self.hide()
            return
        uid = info.get("uid", "")
        block1 = info.get("block1", "")
        card_type, locker_num = self._parse(block1) if block1 else ("Неизвестный формат", None)
        client_name = info.get("client")

        self.lbl_uid.setText("UID: " + uid)
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
        rental = info.get("rental")
        if rental:
            term = "" if rental == "бессрочно" else f"до {rental}"
            self.lbl_rental.setText("🔑 Аренда шкафчика: " + (term or rental))
            self.lbl_rental.setStyleSheet("color: #f59e0b; font-weight: 600;")
        else:
            self.lbl_rental.setText("Аренда шкафчика: нет")
            self.lbl_rental.setStyleSheet("color: #64748b;")
        self.lbl_raw.setText("block_1: " + block1)

        self._restore_or_default_pos()
        self.show()
        self.raise_()

    def _restore_or_default_pos(self):
        if os.path.exists(POS_FILE):
            try:
                pos = json.load(open(POS_FILE, encoding="utf-8"))
                self.move(int(pos.get("x", 100)), int(pos.get("y", 100)))
                return
            except Exception:
                pass
        screen = self.screen().availableGeometry()
        self.move(screen.x() + screen.width() - 440,
                  screen.y() + screen.height() - 320)

    def clear_client(self):
        try:
            if os.path.exists(CACHE_FILE):
                json.dump({}, open(CACHE_FILE, "w", encoding="utf-8"))
        except Exception:
            pass
        self.hide()

    def refresh_card(self):
        pass

    def _parse(self, b1: str):
        b1 = (b1 or "").strip().upper()
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
            tail = b1[14:]
            if all(c == "0" for c in tail) or tail.endswith("03"):
                return ("Индивидуальный режим" if prefix == "0201"
                        else "Режим удаления"), None
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
                bytes_tail = [tail[i:i + 2] for i in range(0, len(tail), 2)]
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
            s, e = i * 2, i * 2 + 2
            if len(b1) >= e:
                try:
                    v = int(b1[s:e], 16)
                    if v > 0:
                        return "Карта клиента", v
                except Exception:
                    pass
        return "Неизвестный формат", None