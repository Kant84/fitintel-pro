"""Login Window"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from api.client import ApiClient


class LoginWindow(QDialog):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.user_info = None
        self.token = None
        self.setWindowTitle("FitIntel Pro - v1.3.0")
        self.setFixedSize(500, 650)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-family: 'Segoe UI', Arial; }
            QLabel#title { font-size: 28px; font-weight: bold; color: #38bdf8; }
            QLabel#subtitle { font-size: 14px; color: #94a3b8; }
            QLineEdit {
                background-color: #1e293b; border: 2px solid #334155;
                border-radius: 8px; padding: 12px 16px;
                color: #f1f5f9; font-size: 14px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
            QPushButton#login_btn {
                background-color: #38bdf8; color: #0f172a;
                border: none; border-radius: 8px; padding: 14px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton#login_btn:hover { background-color: #7dd3fc; }
            QPushButton#login_btn:pressed { background-color: #0ea5e9; }
            QPushButton#test_btn {
                background-color: transparent; color: #64748b;
                border: 1px solid #334155; border-radius: 6px;
                padding: 8px; font-size: 12px;
            }
            QPushButton#test_btn:hover { color: #94a3b8; border-color: #475569; }
            QLabel#status {
                font-size: 13px; padding: 8px; border-radius: 6px;
            }
        """)
        self._build_ui()
        self._center()

    def _center(self):
        screen = self.screen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        title = QLabel("FitIntel Pro")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("CRM + Face ID Терминал v1.3.0")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        self.lbl_status = QLabel("Проверка сервера...")
        self.lbl_status.setObjectName("status")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        layout.addSpacing(10)

        lbl_user = QLabel("Логин")
        lbl_user.setStyleSheet("font-size: 13px; color: #94a3b8;")
        layout.addWidget(lbl_user)
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("admin")
        self.txt_user.setText("admin")
        self.txt_user.returnPressed.connect(self._do_login)
        layout.addWidget(self.txt_user)

        layout.addSpacing(8)

        lbl_pass = QLabel("Пароль")
        lbl_pass.setStyleSheet("font-size: 13px; color: #94a3b8;")
        layout.addWidget(lbl_pass)
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("пароль")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setText("gfhjkmas")
        self.txt_pass.returnPressed.connect(self._do_login)
        layout.addWidget(self.txt_pass)

        layout.addSpacing(16)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setObjectName("login_btn")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        layout.addWidget(self.btn_login)

        layout.addSpacing(8)

        self.btn_test = QPushButton("Проверить подключение")
        self.btn_test.setObjectName("test_btn")
        self.btn_test.clicked.connect(self._test_connection)
        layout.addWidget(self.btn_test)

        version = QLabel("Сборка 2026.06.14 | FitIntel Systems")
        version.setStyleSheet("color: #475569; font-size: 11px; margin-top: 12px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        self._test_connection()

    def _test_connection(self):
        self.lbl_status.setText("Проверка сервера...")
        self.lbl_status.setStyleSheet("font-size: 13px; padding: 8px; border-radius: 6px; background-color: #1e293b; color: #94a3b8;")
        try:
            result = self.api.health()
            status = result.get("status", "unknown")
            module = result.get("module", "")
            db = result.get("database", "")
            msg = "Сервер: " + status.upper() + " | " + module + " | БД: " + db
            self.lbl_status.setText(msg)
            self.lbl_status.setStyleSheet("font-size: 13px; padding: 8px; border-radius: 6px; background-color: #064e3b; color: #6ee7b7;")
        except Exception as e:
            msg = "Сервер недоступен: " + str(e)[:60]
            self.lbl_status.setText(msg)
            self.lbl_status.setStyleSheet("font-size: 13px; padding: 8px; border-radius: 6px; background-color: #450a0a; color: #fca5a5;")

    def _do_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Вход...")
        try:
            result = self.api.login(username, password)
            token = result.get("access_token")
            if not token:
                QMessageBox.critical(self, "Ошибка", "Токен не получен")
                return
            self.api.set_token(token)
            self.user_info = self.api.me()
            self.token = token
            self.accept()
        except Exception as e:
            err = str(e)
            if "401" in err or "403" in err:
                QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль")
            elif "Connection" in err:
                QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к серверу.\nУбедитесь, что бэкенд запущен:\nuvicorn app.main:app --reload --port 8001")
            else:
                QMessageBox.critical(self, "Ошибка", "Ошибка входа: " + err[:200])
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Войти")
