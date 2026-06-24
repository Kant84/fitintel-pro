"""FitIntel Pro — Login Window"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QSizePolicy, QSpacerItem, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon
from api import ApiClient


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
        self.api = ApiClient()
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

        # Logo / Title
        self.title_lbl = QLabel("FitIntel Pro")
        self.title_lbl.setObjectName("title")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Вход в систему управления фитнес-клубом")
        self.sub_lbl.setObjectName("subtitle")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sub_lbl)
        layout.addSpacing(32)

        # Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Login
        lbl_login = QLabel("Логин")
        lbl_login.setObjectName("label")
        card_layout.addWidget(lbl_login)

        self.edit_login = QLineEdit()
        self.edit_login.setPlaceholderText("admin")
        card_layout.addWidget(self.edit_login)

        # Password
        lbl_pass = QLabel("Пароль")
        lbl_pass.setObjectName("label")
        card_layout.addWidget(lbl_pass)

        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("••••••")
        card_layout.addWidget(self.edit_pass)

        # Remember me
        self.chk_remember = QCheckBox("Запомнить меня")
        card_layout.addWidget(self.chk_remember)

        # Button
        card_layout.addSpacing(8)
        self.btn_login = QPushButton("Войти")
        self.btn_login.setObjectName("primary")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._on_login)
        card_layout.addWidget(self.btn_login)

        # Status
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px;")
        card_layout.addWidget(self.lbl_status)

        layout.addWidget(card)
        layout.addStretch()

        # Footer
        footer = QLabel("© 2026 ИП Санакин А.В. | FitIntel Pro v1.3.0")
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

    def _on_success(self, result: dict):
        token = result.get("access_token")
        if not token:
            self._on_error("Нет токена в ответе сервера")
            return

        self.api.set_token(token)
        try:
            user = self.api.me()
        except Exception as e:
            self._on_error(f"Не удалось получить данные пользователя: {e}")
            return

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
