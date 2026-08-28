import sys, json, urllib.request
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

API_BASE = "http://127.0.0.1:8001/api/v1"

def api_post(endpoint, payload):
    try:
        req = urllib.request.Request(f"{API_BASE}{endpoint}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_err": str(e)}

class RFIDMonitorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(320, 180)
        self.setStyleSheet("background-color: #0f172a; color: #e2e8f0; border-radius: 12px; border: 2px solid #334155;")
        self._last_uid = None
        self._build_ui()
        self.hide()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(300)
        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self._do_hide)
        self._hide_timer.setSingleShot(True)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)
        lay.setContentsMargins(12, 10, 12, 10)
        self.status = QLabel("Ожидание...")
        self.status.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.status.setStyleSheet("color: #f59e0b;")
        lay.addWidget(self.status)
        self.lbl_name = QLabel("—")
        self.lbl_name.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #38bdf8;")
        lay.addWidget(self.lbl_name)
        self.lbl_phone = QLabel("—")
        self.lbl_phone.setFont(QFont("Segoe UI", 11))
        self.lbl_phone.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.lbl_phone)
        self.lbl_sub = QLabel("—")
        self.lbl_sub.setFont(QFont("Segoe UI", 12))
        self.lbl_sub.setStyleSheet("color: #10b981;")
        lay.addWidget(self.lbl_sub)
        self.lbl_locker = QLabel("—")
        self.lbl_locker.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_locker.setStyleSheet("color: #f472b6;")
        lay.addWidget(self.lbl_locker)

    def _poll(self):
        r = api_post("/reader/detect-card", {})
        uid = None
        if "_err" not in r:
            uid = r.get("uid")
        if uid:
            self._hide_timer.stop()
            if uid != self._last_uid:
                self._last_uid = uid
                scan = api_post("/rfid/scan", {"card_uid": uid, "device_id": "ACS-ACR1252-001"})
                if "_err" not in scan and scan.get("found"):
                    self._show_client(scan)
                else:
                    self._show_unknown(uid)
        else:
            if self._last_uid is not None and not self._hide_timer.isActive():
                self._hide_timer.start(1000)  # 1 сек после уборки

    def _do_hide(self):
        self._last_uid = None
        self.hide()

    def _show_client(self, data):
        self.lbl_name.setText(data.get("full_name", "—"))
        self.lbl_phone.setText(data.get("phone", "—"))
        self.lbl_sub.setText("Абонемент: " + data.get("subscription_name", "-"))
        locker = data.get("locker_number")
        self.lbl_locker.setText("🔒 Шкафчик №" + str(locker) if locker else "🔓 Шкафчик не занят")
        self.status.setText("🟢 Доступ разрешен" if data.get("access_granted") else "🔴 Доступ запрещен")
        self.status.setStyleSheet("color: #10b981;" if data.get("access_granted") else "color: #ef4444;")
        self._show()

    def _show_unknown(self, uid):
        self.lbl_name.setText("Неизвестная карта")
        self.lbl_phone.setText(uid)
        self.lbl_sub.setText("—")
        self.lbl_locker.setText("—")
        self.status.setText("🔴 Карта не найдена")
        self.status.setStyleSheet("color: #ef4444;")
        self._show()

    def _show(self):
        screen = self.screen().geometry()
        self.move(screen.width() - 340, screen.height() - 200)
        self.show()
        self.raise_()
