"""Settings Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFormLayout, QComboBox, QSpinBox, QMessageBox
from PyQt6.QtCore import Qt
from api.client import ApiClient


class SettingsTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Settings")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        conn = QWidget()
        conn.setStyleSheet("QWidget { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 16px; }")
        cl = QFormLayout(conn)
        cl.setSpacing(12)
        lbl_conn = QLabel("API Connection")
        lbl_conn.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        cl.addRow(lbl_conn)
        self.txt_api_url = QLineEdit()
        self.txt_api_url.setText("http://localhost:8001/api/v1")
        self.txt_api_url.setStyleSheet("QLineEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; } QLineEdit:focus { border-color: #38bdf8; }")
        cl.addRow("API Base URL", self.txt_api_url)
        self.txt_timeout = QSpinBox()
        self.txt_timeout.setRange(1, 60)
        self.txt_timeout.setValue(10)
        self.txt_timeout.setStyleSheet("QSpinBox { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 6px; color: #e2e8f0; }")
        cl.addRow("Timeout (sec)", self.txt_timeout)
        btn_test = QPushButton("Test Connection")
        btn_test.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_test.clicked.connect(self._test_connection)
        cl.addRow(btn_test)
        self.lbl_conn_status = QLabel("Not tested")
        self.lbl_conn_status.setStyleSheet("color: #94a3b8; font-size: 13px;")
        cl.addRow(self.lbl_conn_status)
        layout.addWidget(conn)

        face = QWidget()
        face.setStyleSheet("QWidget { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 16px; }")
        fl = QFormLayout(face)
        fl.setSpacing(12)
        lbl_face = QLabel("Face ID")
        lbl_face.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        fl.addRow(lbl_face)
        self.txt_face_thresh = QComboBox()
        self.txt_face_thresh.addItems(["0.6 (Strict)", "0.5 (Normal)", "0.4 (Loose)"])
        self.txt_face_thresh.setStyleSheet("QComboBox { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 6px; color: #e2e8f0; }")
        fl.addRow("Default threshold", self.txt_face_thresh)
        self.txt_terminal_id = QLineEdit()
        self.txt_terminal_id.setText("desktop-001")
        self.txt_terminal_id.setStyleSheet("QLineEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; }")
        fl.addRow("Terminal ID", self.txt_terminal_id)
        layout.addWidget(face)

        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #34d399; }")
        btn_save.clicked.connect(lambda: QMessageBox.information(self, "Settings", "Settings saved (in-memory only)"))
        layout.addWidget(btn_save)
        layout.addStretch()

        version = QLabel("FitIntel Pro Desktop v1.3.0 | Build 2026.06.14")
        version.setStyleSheet("color: #475569; font-size: 11px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

    def _test_connection(self):
        url = self.txt_api_url.text().strip()
        try:
            import requests
            resp = requests.get(url.replace("/api/v1", "") + "/api/v1/health/", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.lbl_conn_status.setText("Connected | Status: " + data.get("status", "?").upper() + " | DB: " + data.get("database", "?"))
                self.lbl_conn_status.setStyleSheet("color: #10b981; font-size: 13px; font-weight: bold;")
            else:
                self.lbl_conn_status.setText("Error: HTTP " + str(resp.status_code))
                self.lbl_conn_status.setStyleSheet("color: #f87171; font-size: 13px;")
        except Exception as e:
            self.lbl_conn_status.setText("Failed: " + str(e)[:80])
            self.lbl_conn_status.setStyleSheet("color: #f87171; font-size: 13px;")
