#!/usr/bin/env python3
"""E16: RFID Monitor — отдельное окно для отображения клиента при считывании."""
import sys
import json
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
    QHBoxLayout, QFrame, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QIcon, QAction

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
    except Exception as e:
        return {"_err": str(e)}

class RFIDMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RFID Monitor — FitIntel Pro")
        self.setMinimumSize(500, 300)
        self.setStyleSheet("background-color: #0f172a; color: #e2e8f0;")
        self._last_uid = None
        self._build_ui()
        self._start_polling()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("🔒 RFID Monitor")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #ec4899;")
        lay.addWidget(header)

        # Status
        self.status = QLabel("🟡  Ожидание карты...")
        self.status.setFont(QFont("Segoe UI", 14))
        self.status.setStyleSheet("color: #f59e0b;")
        lay.addWidget(self.status)

        # Client info card
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 12px;
                border: 2px solid #334155;
                padding: 16px;
            }
        """)
        card_lay = QVBoxLayout(self.card)
        card_lay.setSpacing(8)

        self.lbl_name = QLabel("—")
        self.lbl_name.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #38bdf8;")
        card_lay.addWidget(self.lbl_name)

        self.lbl_phone = QLabel("—")
        self.lbl_phone.setFont(QFont("Segoe UI", 12))
        self.lbl_phone.setStyleSheet("color: #94a3b8;")
        card_lay.addWidget(self.lbl_phone)

        self.lbl_sub = QLabel("—")
        self.lbl_sub.setFont(QFont("Segoe UI", 14))
        self.lbl_sub.setStyleSheet("color: #10b981;")
        card_lay.addWidget(self.lbl_sub)

        self.lbl_expires = QLabel("—")
        self.lbl_expires.setFont(QFont("Segoe UI", 12))
        self.lbl_expires.setStyleSheet("color: #f472b6;")
        card_lay.addWidget(self.lbl_expires)

        lay.addWidget(self.card)
        lay.addStretch(1)

    def _start_polling(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(500)

    def _poll(self):
        r = api_post("/reader/detect-card", {})
        if "_err" in r:
            return
        uid = r.get("uid")
        if not uid or uid == self._last_uid:
            return
        self._last_uid = uid

        scan = api_post("/rfid/scan", {"card_uid": uid, "device_id": "ACS-ACR1252-001"})
        if "_err" in scan or not scan.get("found"):
            self.status.setText("🔴  Карта не найдена")
            self.status.setStyleSheet("color: #ef4444;")
            self.lbl_name.setText("Неизвестная карта")
            self.lbl_phone.setText(uid)
            self.lbl_sub.setText("—")
            self.lbl_expires.setText("—")
            return

        self.status.setText("🟢  Доступ разрешен")
        self.status.setStyleSheet("color: #10b981;")
        self.lbl_name.setText(scan.get("full_name", "—"))
        self.lbl_phone.setText(scan.get("phone", "—"))
        sub = scan.get("subscription_name", "—")
        exp = scan.get("subscription_expires", "—")
        self.lbl_sub.setText(f"Абонемент: {sub}")
        self.lbl_expires.setText(f"Действует до: {exp}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = RFIDMonitor()
    w.show()
    sys.exit(app.exec())
