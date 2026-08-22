"""FitIntel Pro — License Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QMessageBox, QFrame, QTextEdit, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api import ApiClient
from windows import theme


class VerifyLicenseWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient, license_key: str, device_id: str):
        super().__init__()
        self.api = api
        self.license_key = license_key
        self.device_id = device_id

    def run(self):
        try:
            result = self.api.verify_license(self.license_key, self.device_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LicenseTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("🔐 Лицензирование системы")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)

        # Status card
        self.card_status = QFrame()
        self.card_status.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;")
        card_layout = QVBoxLayout(self.card_status)
        self.lbl_status = QLabel("⏳ Проверьте лицензию")
        self.lbl_status.setStyleSheet("font-size: 14px; color: #475569;")
        card_layout.addWidget(self.lbl_status)
        layout.addWidget(self.card_status)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        self.edit_key = QLineEdit()
        self.edit_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.edit_key.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-family: monospace;")
        form.addRow("Лицензионный ключ:", self.edit_key)

        self.edit_device = QLineEdit()
        self.edit_device.setText("desktop-001")
        self.edit_device.setStyleSheet("padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px;")
        form.addRow("ID устройства:", self.edit_device)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_verify = QPushButton("✅ Проверить лицензию")
        btn_verify.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: 600; } QPushButton:hover { background: #059669; }")
        btn_verify.clicked.connect(self._verify)
        btn_layout.addWidget(btn_verify)

        btn_limits = QPushButton("📊 Проверить лимиты")
        btn_limits.setStyleSheet("QPushButton { background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: 600; } QPushButton:hover { background: #2563eb; }")
        btn_limits.clicked.connect(self._check_limits)
        btn_layout.addWidget(btn_limits)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Info area
        self.info_area = QTextEdit()
        self.info_area.setReadOnly(True)
        self.info_area.setPlaceholderText("Информация о лицензии появится здесь...")
        self.info_area.setStyleSheet(theme.card_style())
        self.info_area.setMaximumHeight(200)
        layout.addWidget(self.info_area)

        layout.addStretch()

        # Footer
        footer = QLabel("© 2026 ИП Санакин А.В. | Лицензирование через API v1.3.0")
        footer.setStyleSheet("font-size: 11px; color: #94a3b8;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def _verify(self):
        key = self.edit_key.text().strip()
        device = self.edit_device.text().strip()

        if not key or not device:
            QMessageBox.warning(self, "Ошибка", "Введите ключ и ID устройства")
            return

        self.lbl_status.setText("⏳ Проверка лицензии...")
        self.worker = VerifyLicenseWorker(self.api, key, device)
        self.worker.finished.connect(self._on_verify_success)
        self.worker.error.connect(self._on_verify_error)
        self.worker.start()

    def _on_verify_success(self, result: dict):
        valid = result.get("valid", False)
        message = result.get("message", "—")
        info = result.get("info", {})

        if valid:
            self.card_status.setStyleSheet("background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 16px;")
            self.lbl_status.setStyleSheet("font-size: 14px; color: #065f46; font-weight: 600;")
            self.lbl_status.setText(f"✅ Лицензия ВАЛИДНА\n{message}")
        else:
            self.card_status.setStyleSheet("background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;")
            self.lbl_status.setStyleSheet("font-size: 14px; color: #991b1b; font-weight: 600;")
            self.lbl_status.setText(f"❌ Лицензия НЕВАЛИДНА\n{message}")

        self.info_area.setText(str(info))

    def _on_verify_error(self, msg: str):
        self.card_status.setStyleSheet("background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;")
        self.lbl_status.setStyleSheet("font-size: 14px; color: #991b1b;")
        self.lbl_status.setText(f"❌ Ошибка: {msg}")

    def _check_limits(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Ошибка", "Введите лицензионный ключ")
            return
        try:
            result = self.api.get_license_limits(key)
            self.info_area.setText(str(result))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


# === E64_LICENSE: key check panel ===
try:
    from PyQt6.QtWidgets import QWidget as _W64, QHBoxLayout as _H64, QVBoxLayout as _V64, QLineEdit as _E64, QPushButton as _B64, QLabel as _L64, QMessageBox as _M64
    import requests as _rq64
    _e64_orig = LicenseTab.__init__
    def _e64_init(self, *a, **kw):
        _e64_orig(self, *a, **kw)
        try:
            panel = _W64(); v = _V64(panel)
            v.addWidget(_L64("Проверка лицензионного ключа (из License Studio):"))
            row = _H64()
            ed = _E64(); ed.setPlaceholderText("FIPRO-.....")
            row.addWidget(ed)
            btn = _B64("✔ Проверить"); row.addWidget(btn)
            v.addLayout(row)
            res = _L64("—"); res.setWordWrap(True)
            v.addWidget(res)
            def _check():
                key = ed.text().strip()
                if not key:
                    return
                api = getattr(self, "api", None)
                base = getattr(api, "base_url", None) or getattr(api, "base", None) or "http://localhost:8001/api/v1"
                try:
                    r = _rq64.post(str(base).rstrip("/") + "/license/validate", json={"key": key}, timeout=15).json()
                    if r.get("valid"):
                        res.setText("✅ Лицензия ДЕЙСТВИТЕЛЬНА: тариф %s, до %s, клиентов: %s, клуб: %s" % (
                            r.get("plan"), r.get("exp"), r.get("max_clients"), r.get("club")))
                        res.setStyleSheet("color:#39ff14; font-weight:bold;")
                    else:
                        res.setText("❌ Недействительна: %s" % r.get("reason", "?"))
                        res.setStyleSheet("color:#ff3860; font-weight:bold;")
                except Exception as e:
                    res.setText("Ошибка проверки: %s" % e)
            btn.clicked.connect(_check)
            lay = self.layout()
            if lay is not None:
                lay.addWidget(panel)
        except Exception as e:
            print("license panel:", e)
    LicenseTab.__init__ = _e64_init
    print("E64 license panel OK")
except Exception as e:
    print("E64 FAIL:", e)
