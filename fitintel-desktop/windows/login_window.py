"""FitIntel Pro — Login Window"""
import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QSizePolicy, QSpacerItem, QCheckBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon
from api import ApiClient

from paths import SETTINGS as SETTINGS_PATH

def _load_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


class LoginWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient, username: str, password: str):
        super().__init__()
        self.api = api
        self.username = username
        self.password = password

    def run(self):
        try:
            result = self.api.login(self.username, self.password)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LoginWindow(QWidget):
    login_success = pyqtSignal(dict, str)  # user_data, token

    def __init__(self):
        super().__init__()
        # API base из client_settings.json — ВАЖНО: при ошибке чтения будет localhost!
        _cfg = _load_settings()
        self.api = ApiClient(base_url=_cfg.get("api_base", "http://localhost:8001/api/v1"))
        self.setWindowTitle("FitIntel Pro — Авторизация")
        self.setFixedSize(480, 560)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._center()

    def _stylesheet(self) -> str:
        return """
        QWidget {
            background-color: #f8fafc;
            font-family: "Segoe UI", "Helvetica Neue", sans-serif;
            color: #1e293b;
        }
        QFrame#card {
            background-color: #ffffff;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
        }
        QLabel#title {
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
        }
        QLabel#subtitle {
            font-size: 13px;
            color: #64748b;
        }
        QLabel#label {
            font-size: 13px;
            font-weight: 600;
            color: #334155;
            margin-bottom: 4px;
        }
        QLineEdit {
            padding: 10px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 14px;
            background: #ffffff;
        }
        QLineEdit:focus {
            border: 1px solid #10b981;
        }
        QPushButton#primary {
            background-color: #10b981;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
        }
        QPushButton#primary:hover {
            background-color: #059669;
        }
        QPushButton#primary:pressed {
            background-color: #047857;
        }
        QPushButton#primary:disabled {
            background-color: #94a3b8;
        }
        QCheckBox {
            font-size: 12px;
            color: #64748b;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
        }
        QCheckBox::indicator:checked {
            background-color: #10b981;
            border: 1px solid #10b981;
        }
        """

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        self.title_lbl = QLabel("FitIntel Pro")
        self.title_lbl.setObjectName("title")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Вход в систему управления фитнес-клубом")
        self.sub_lbl.setObjectName("subtitle")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sub_lbl)
        layout.addSpacing(32)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        lbl_login = QLabel("Логин")
        lbl_login.setObjectName("label")
        card_layout.addWidget(lbl_login)

        self.edit_login = QLineEdit()
        self.edit_login.setPlaceholderText("admin")
        card_layout.addWidget(self.edit_login)

        lbl_pass = QLabel("Пароль")
        lbl_pass.setObjectName("label")
        card_layout.addWidget(lbl_pass)

        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("••••••")
        card_layout.addWidget(self.edit_pass)

        self.chk_remember = QCheckBox("Запомнить меня")
        self._load_saved_credentials()
        card_layout.addWidget(self.chk_remember)

        card_layout.addSpacing(8)
        self.btn_login = QPushButton("Войти")
        self.btn_login.setObjectName("primary")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._on_login)
        card_layout.addWidget(self.btn_login)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px;")
        card_layout.addWidget(self.lbl_status)

        layout.addWidget(card)
        layout.addStretch()

        footer = QLabel(" 2026 FitIntel Pro v1.6.1")
        footer.setStyleSheet("font-size: 11px; color: #94a3b8;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _on_login(self):
        username = self.edit_login.text().strip()
        password = self.edit_pass.text().strip()

        if not username or not password:
            self.lbl_status.setText("Введите логин и пароль")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Вход...")
        self.lbl_status.setText("")

        self.worker = LoginWorker(self.api, username, password)
        self.worker.finished.connect(self._on_success)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _load_saved_credentials(self):
        try:
            st = _load_settings()
            if st.get("remember_login"):
                self.edit_login.setText(st.get("saved_login", ""))
                self.edit_pass.setText(st.get("saved_password", ""))
                self.chk_remember.setChecked(True)
        except Exception:
            pass

    def _save_credentials(self):
        try:
            st = _load_settings()
            if self.chk_remember.isChecked():
                st["remember_login"] = True
                st["saved_login"] = self.edit_login.text().strip()
                st["saved_password"] = self.edit_pass.text()
            else:
                st["remember_login"] = False
                st.pop("saved_login", None)
                st.pop("saved_password", None)
            SETTINGS_PATH.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _on_success(self, result: dict):
        token = result.get("access_token")
        if not token:
            self._on_error("Нет токена в ответе сервера")
            return

        self.api.set_token(token)
        self.api.set_token(token)

        # E70: сохраняем refresh_token для молчаливого обновления сессии
        rt = result.get("refresh_token")
        if rt:
            try:
                st = _load_settings()
                st["refresh_token"] = rt
                SETTINGS_PATH.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
                self.api._refresh_token = rt
            except Exception:
                pass
        if result.get("force_change_password"):
            from windows.change_password_dialog import ChangePasswordDialog
            dlg = ChangePasswordDialog(self.api, token, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self._on_error("Необходимо сменить временный пароль")
                return

        try:
            user = self.api.me()
        except Exception as e:
            self._on_error(f"Не удалось получить данные пользователя: {e}")
            return

        try:
            from app_logging import log as _log
            _log.info("Успешный вход: %s", user.get("username", "?"))
        except Exception:
            pass
        self._save_credentials()
        self.login_success.emit(user, token)
        self.close()

    def _on_error(self, msg: str):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Войти")
        self.lbl_status.setText(f"Ошибка: {msg}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._on_login()
        else:
            super().keyPressEvent(event)