"""Main Window"""
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, QStatusBar, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from api.client import ApiClient
from .clients_tab import ClientsTab
from .subscriptions_tab import SubscriptionsTab
from .visits_tab import VisitsTab
from .face_id_tab import FaceIDTab
from .license_tab import LicenseTab
from .settings_tab import SettingsTab
from .cash_desk_tab import CashDeskTab
from .access_tab import AccessTab
from .analytics_tab import AnalyticsTab
from .users_tab import UsersTab


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient, user: dict, token: str):
        super().__init__()
        self.api = api
        self.user = user
        self.token = token
        self.roles = user.get("roles", [])
        self.permissions = user.get("permissions", [])
        self._build_ui()

    def _has_permission(self, perm: str) -> bool:
        return perm in self.permissions or "admin" in self.roles

    def _is_admin(self) -> bool:
        return "admin" in self.roles or "superadmin" in self.roles

    def _build_ui(self):
        self.setWindowTitle("FitIntel Pro v1.3.0 - Администратор")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget#header { background-color: #1e293b; border-bottom: 2px solid #38bdf8; }
            QLabel#header_title { color: #38bdf8; font-weight: bold; }
            QLabel#header_ver { color: #64748b; font-size: 12px; }
            QLabel#header_user { color: #94a3b8; font-size: 13px; }
            QPushButton#header_logout { background-color: transparent; color: #f87171; border: 1px solid #f87171; border-radius: 6px; padding: 6px 16px; font-size: 12px; }
            QPushButton#header_logout:hover { background-color: #f87171; color: #0f172a; }
            QTabWidget::pane { border: none; background-color: #0f172a; }
            QTabBar::tab { background-color: #1e293b; color: #94a3b8; padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; font-size: 13px; }
            QTabBar::tab:selected { background-color: #38bdf8; color: #0f172a; font-weight: bold; }
            QTabBar::tab:hover:!selected { background-color: #334155; color: #e2e8f0; }
            QStatusBar { background-color: #1e293b; color: #94a3b8; font-size: 12px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(56)
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("FitIntel Pro")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setObjectName("header_title")
        hlayout.addWidget(title)

        ver = QLabel("v1.3.0")
        ver.setObjectName("header_ver")
        hlayout.addWidget(ver)
        hlayout.addStretch()

        role_text = ", ".join(self.roles) if self.roles else "пользователь"
        user_label = QLabel("Пользователь: " + str(self.user.get("username", "-")) + "  |  Роль: " + role_text)
        user_label.setObjectName("header_user")
        hlayout.addWidget(user_label)

        btn_logout = QPushButton("Выход")
        btn_logout.setObjectName("header_logout")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.clicked.connect(self._logout)
        hlayout.addWidget(btn_logout)

        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)

        # All users see Dashboard
        self.tabs.addTab(AnalyticsTab(self.api, self.user), "Дашборд")

        # Admin/Manager tabs
        if self._is_admin() or self._has_permission("clients.read"):
            self.tabs.addTab(ClientsTab(self.api, self.user), "Клиенты")
        if self._is_admin() or self._has_permission("subscriptions.read"):
            self.tabs.addTab(SubscriptionsTab(self.api, self.user), "Абонементы")
        if self._is_admin() or self._has_permission("visits.read"):
            self.tabs.addTab(VisitsTab(self.api, self.user), "Посещения")
        if self._is_admin() or self._has_permission("cash.read"):
            self.tabs.addTab(CashDeskTab(self.api, self.user), "Касса")
        if self._is_admin() or self._has_permission("access.read"):
            self.tabs.addTab(AccessTab(self.api, self.user), "СКУД")
        if self._is_admin() or self._has_permission("face_id.read"):
            self.tabs.addTab(FaceIDTab(self.api, self.user), "Face ID")

        # Admin only
        if self._is_admin():
            self.tabs.addTab(UsersTab(self.api, self.user), "Пользователи")
            self.tabs.addTab(LicenseTab(self.api, self.user), "Лицензия")
            self.tabs.addTab(SettingsTab(self.api, self.user), "Настройки")

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_server)
        self.timer.start(30000)

    def _logout(self):
        reply = QMessageBox.question(self, "Confirm", "Logout?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.api.clear_token()
            self.close()

    def _check_server(self):
        try:
            result = self.api.health()
            self.status.showMessage("Сервер: " + result.get("status", "?").upper() + " | localhost:8001 | " + str(self.user.get("username", "-"))[:20], 30000)
        except Exception:
            self.status.showMessage("Сервер: НЕДОСТУПЕН", 30000)
