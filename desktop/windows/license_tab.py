"""License Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt
from api.client import ApiClient


class LicenseTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("License Management")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        check_frame = QWidget()
        check_frame.setStyleSheet("QWidget { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 16px; }")
        cl = QVBoxLayout(check_frame)
        cl.setSpacing(12)
        lbl_check = QLabel("Check License")
        lbl_check.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        cl.addWidget(lbl_check)
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        lbl_key = QLabel("License Key:")
        lbl_key.setStyleSheet("color: #94a3b8; font-size: 13px;")
        row1.addWidget(lbl_key)
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("FITINTEL-XXXX-XXXX-XXXX")
        self.txt_key.setStyleSheet("QLineEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        row1.addWidget(self.txt_key, 1)
        lbl_dev = QLabel("Device ID:")
        lbl_dev.setStyleSheet("color: #94a3b8; font-size: 13px;")
        row1.addWidget(lbl_dev)
        self.txt_device = QLineEdit()
        self.txt_device.setPlaceholderText("DESKTOP-001")
        self.txt_device.setStyleSheet("QLineEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        row1.addWidget(self.txt_device, 1)
        cl.addLayout(row1)
        btn_check = QPushButton("Verify License")
        btn_check.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_check.clicked.connect(self._verify)
        cl.addWidget(btn_check)
        self.lbl_result = QLabel("Enter license key and device ID to verify")
        self.lbl_result.setStyleSheet("color: #94a3b8; font-size: 13px; padding: 8px;")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.lbl_result)
        layout.addWidget(check_frame)

        limits_frame = QWidget()
        limits_frame.setStyleSheet("QWidget { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 16px; }")
        ll = QVBoxLayout(limits_frame)
        lbl_limits = QLabel("License Limits")
        lbl_limits.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")
        ll.addWidget(lbl_limits)
        self.txt_limits = QTextEdit()
        self.txt_limits.setReadOnly(True)
        self.txt_limits.setMaximumHeight(120)
        self.txt_limits.setStyleSheet("QTextEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; }")
        self.txt_limits.setText("Click 'Verify License' to see limits")
        ll.addWidget(self.txt_limits)
        layout.addWidget(limits_frame)

        btn_refresh = QPushButton("Refresh Status")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self._check_limits)
        layout.addWidget(btn_refresh)
        layout.addStretch()

    def _verify(self):
        key = self.txt_key.text().strip()
        device = self.txt_device.text().strip()
        if not key or not device: QMessageBox.warning(self, "Error", "Enter license key and device ID"); return
        try:
            result = self.api.verify_license(key, device)
            valid = result.get("valid", False)
            if valid:
                self.lbl_result.setText("VALID | Type: " + str(result.get("type", "-")) + " | Expires: " + str(result.get("expires_at", "-")))
                self.lbl_result.setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold; padding: 8px; background-color: #064e3b; border-radius: 6px;")
            else:
                self.lbl_result.setText("INVALID | " + result.get("reason", "Invalid license"))
                self.lbl_result.setStyleSheet("color: #f87171; font-size: 14px; font-weight: bold; padding: 8px; background-color: #450a0a; border-radius: 6px;")
            self._show_limits(result)
        except Exception as e:
            self.lbl_result.setText("ERROR: " + str(e)[:100])
            self.lbl_result.setStyleSheet("color: #f87171; font-size: 14px; font-weight: bold; padding: 8px; background-color: #450a0a; border-radius: 6px;")

    def _check_limits(self):
        key = self.txt_key.text().strip()
        if not key: QMessageBox.warning(self, "Error", "Enter license key first"); return
        try:
            result = self.api.get_license_limits(key)
            self._show_limits(result)
        except Exception as e: self.txt_limits.setText("Error: " + str(e)[:200])

    def _show_limits(self, data):
        if not isinstance(data, dict): self.txt_limits.setText("No limit data"); return
        lines = [k + ": " + str(v) for k, v in data.items()]
        self.txt_limits.setText("\n".join(lines) if lines else "No limits configured")
