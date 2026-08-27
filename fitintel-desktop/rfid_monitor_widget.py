"""E16: RFID Monitor Widget — компактный, без артефактов."""
import json
import urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

API_BASE = "http://127.0.0.1:8001/api/v1"

def api_post(endpoint: str, payload: dict) -> dict:
    try:
        req = urllib.request.Request(
            f"{API_BASE}{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return {"_err": "API error"}

class RFIDMonitorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFixedSize(300, 160)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #475569; }
            QPushButton:pressed { background-color: #1e293b; }
            QLabel { border: none; background: transparent; }
        """)
        self._last_uid = None
        self._build_ui()
        self.hide()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(500)
        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self.hide)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(4)
        lay.setContentsMargins(10, 8, 10, 8)
        
        header = QHBoxLayout()
        self.status = QLabel("🟡 Ожидание...")
        self.status.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.status.setStyleSheet("color: #f59e0b;")
        header.addWidget(self.status)
        header.addStretch(1)
        
        btn = QPushButton("✕")
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.hide)
        header.addWidget(btn)
        lay.addLayout(header)
        
        self.lbl_name = QLabel("—")
        self.lbl_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #38bdf8;")
        lay.addWidget(self.lbl_name)
        
        self.lbl_phone = QLabel("—")
        self.lbl_phone.setFont(QFont("Segoe UI", 9))
        self.lbl_phone.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.lbl_phone)
        
        self.lbl_sub = QLabel("—")
        self.lbl_sub.setFont(QFont("Segoe UI", 10))
        self.lbl_sub.setStyleSheet("color: #10b981;")
        lay.addWidget(self.lbl_sub)
        
        self.lbl_locker = QLabel("—")
        self.lbl_locker.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_locker.setStyleSheet("color: #f472b6;")
        lay.addWidget(self.lbl_locker)

    def _poll(self):
        r = api_post("/reader/detect-card", {})
        if "_err" in r:
            return
        uid = r.get("uid")
        if not uid or uid == self._last_uid:
            return
        self._last_uid = uid
        scan = api_post("/rfid/scan", {"card_uid": uid, "device_id": "ACS-ACR1252-001"})
        if "_err" not in scan and scan.get("found"):
            self._show_client(scan)
        else:
            self._show_unknown(uid)

    def _show_client(self, data: dict):
        self.lbl_name.setText(data.get("full_name", "—"))
        self.lbl_phone.setText(data.get("phone", "—"))
        sub = data.get("subscription_name", "—")
        self.lbl_sub.setText(f"Абонемент: {sub}")
        locker = data.get("locker_number")
        if locker:
            self.lbl_locker.setText(f"🔒 Шкафчик №{locker}")
        else:
            self.lbl_locker.setText("🔓 Шкафчик не занят")
        if data.get("access_granted"):
            self.status.setText("🟢 Доступ разрешен")
            self.status.setStyleSheet("color: #10b981;")
        else:
            self.status.setText("🔴 Доступ запрещен")
            self.status.setStyleSheet("color: #ef4444;")
        screen = self.screen().geometry()
        self.move(screen.width() - 320, screen.height() - 180)
        self.show()
        self.raise_()
        self._hide_timer.start(5000)

    def _show_unknown(self, uid: str):
        self.status.setText("🔴 Карта не найдена")
        self.status.setStyleSheet("color: #ef4444;")
        self.lbl_name.setText("Неизвестная карта")
        self.lbl_phone.setText(uid)
        self.lbl_sub.setText("—")
        self.lbl_locker.setText("—")
        screen = self.screen().geometry()
        self.move(screen.width() - 320, screen.height() - 180)
        self.show()
        self.raise_()
        self._hide_timer.start(5000)
