#!/usr/bin/env python3
"""E16: RFID Monitor — System Tray с шкафчиком."""
import sys, json, urllib.request
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QAction

API_BASE = "http://127.0.0.1:8001/api/v1"

def api_post(endpoint: str, payload: dict) -> dict:
    try:
        req = urllib.request.Request(f"{API_BASE}{endpoint}",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_err": str(e)}

class RFIDPopup(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setMinimumSize(420, 260)
        self.setStyleSheet("background-color: #0f172a; color: #e2e8f0; border-radius: 16px;")
        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self.hide)
        self._build_ui()
        self.hide()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        self.status = QLabel("🟡 Ожидание...")
        self.status.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.status.setStyleSheet("color: #f59e0b;")
        lay.addWidget(self.status)

        self.lbl_name = QLabel("—")
        self.lbl_name.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #38bdf8;")
        lay.addWidget(self.lbl_name)

        self.lbl_phone = QLabel("—")
        self.lbl_phone.setFont(QFont("Segoe UI", 12))
        self.lbl_phone.setStyleSheet("color: #94a3b8;")
        lay.addWidget(self.lbl_phone)

        self.lbl_sub = QLabel("—")
        self.lbl_sub.setFont(QFont("Segoe UI", 14))
        self.lbl_sub.setStyleSheet("color: #10b981;")
        lay.addWidget(self.lbl_sub)

        self.lbl_locker = QLabel("—")
        self.lbl_locker.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_locker.setStyleSheet("color: #f472b6;")
        lay.addWidget(self.lbl_locker)

        self.lbl_expires = QLabel("—")
        self.lbl_expires.setFont(QFont("Segoe UI", 12))
        self.lbl_expires.setStyleSheet("color: #a78bfa;")
        lay.addWidget(self.lbl_expires)

    def show_client(self, data: dict):
        self.lbl_name.setText(data.get("full_name", "—"))
        self.lbl_phone.setText(data.get("phone", "—"))
        sub = data.get("subscription_name", "—")
        self.lbl_sub.setText(f"Абонемент: {sub}")
        
        locker = data.get("locker_number")
        if locker:
            self.lbl_locker.setText(f"🔒 Шкафчик №{locker}")
        else:
            self.lbl_locker.setText("🔓 Шкафчик не занят")
        
        exp = data.get("subscription_expires", "—")
        self.lbl_expires.setText(f"До: {exp}")
        
        if data.get("access_granted"):
            self.status.setText("🟢 Доступ разрешен")
            self.status.setStyleSheet("color: #10b981;")
        else:
            self.status.setText("🔴 Доступ запрещен")
            self.status.setStyleSheet("color: #ef4444;")
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 440, screen.height() - 280)
        self.show()
        self.raise_()
        self._hide_timer.start(10000)

class RFIDTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("RFID Monitor — FitIntel Pro")
        menu = QMenu()
        show_action = QAction("Показать", self.app)
        show_action.triggered.connect(lambda: self.popup.show_client({"full_name": "Ожидание..."}))
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Выход", self.app)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.popup = RFIDPopup()
        self._last_uid = None
        self._timer = QTimer()
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
        if "_err" not in scan and scan.get("found"):
            self.popup.show_client(scan)
        else:
            self.popup.show_client({"full_name": "Неизвестная карта", "phone": uid, "access_granted": False})

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = RFIDTrayApp()
    app.run()
