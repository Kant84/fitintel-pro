"""FitIntel Pro — Main Window (вкладки строятся из /ui-config/my по роли)"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QStatusBar, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction

from api import ApiClient
from windows.clients_tab import ClientsTab
from windows.subscriptions_tab import SubscriptionsTab
from windows.visits_tab import VisitsTab
from windows.face_id_tab import FaceIDTab
from windows.license_tab import LicenseTab
from windows.settings_tab import SettingsTab
from windows.dashboard_tab import DashboardTab
from windows.payments_tab import PaymentsTab
from windows.users_tab import UsersTab
from windows.devices_tab import DevicesTab
from windows.ui_config_tab import UiConfigTab

# реестр: код экрана -> (заголовок вкладки, класс)
TAB_REGISTRY = {
    "dashboard":     ("Главная", DashboardTab),
    "analytics":     ("Аналитика", DashboardTab),
    "clients":       ("Клиенты", ClientsTab),
    "subscriptions": ("Абонементы", SubscriptionsTab),
    "visits":        ("Входы/Выходы", VisitsTab),
    "payments":      ("Платежи", PaymentsTab),
    "users":         ("Пользователи", UsersTab),
    "devices":       ("Устройства", DevicesTab),
    "face_id":       ("Face ID", FaceIDTab),
    "license":       ("Лицензия", LicenseTab),
    "ui_config":     ("Экраны ролей", UiConfigTab),
    "settings":      ("Настройки", SettingsTab),
}

# порядок по умолчанию, если /ui-config/my недоступен
DEFAULT_TABS = ["dashboard", "clients", "subscriptions", "visits", "payments",
                "users", "devices", "face_id", "license", "ui_config", "settings"]


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, api: ApiClient, user_data: dict, token: str):
        super().__init__()
        self.api = api
        self.user = user_data
        self.token = token
        self.setWindowTitle("FitIntel Pro — Система управления")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._start_health_check()

    def _stylesheet(self) -> str:
        return """
        QMainWindow { background-color: #f1f5f9; }
        QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; background: #ffffff; top: -1px; }
        QTabBar::tab {
            background: #e2e8f0; color: #475569; padding: 10px 16px; margin-right: 4px;
            border-top-left-radius: 8px; border-top-right-radius: 8px;
            font-weight: 600; font-size: 13px;
        }
        QTabBar::tab:selected { background: #ffffff; color: #0f172a; border-bottom: 2px solid #10b981; }
        QTabBar::tab:hover:!selected { background: #cbd5e1; }
        QLabel#header-title { font-size: 20px; font-weight: 700; color: #0f172a; }
        QLabel#header-user { font-size: 12px; color: #64748b; }
        QPushButton#logout {
            background: transparent; color: #ef4444; border: 1px solid #ef4444;
            border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton#logout:hover { background: #ef4444; color: white; }
        QStatusBar { background: #ffffff; color: #64748b; font-size: 12px; border-top: 1px solid #e2e8f0; }
        """

    def _visible_screen_codes(self) -> list:
        """Запрашивает у бэка экраны роли (E51). Fallback — полный набор."""
        try:
            data = self.api.get_ui_my()
            codes = [s["code"] for s in data.get("screens", [])]
            if codes:
                return codes
        except Exception:
            pass
        return list(DEFAULT_TABS)

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        added = set()
        for code in self._visible_screen_codes():
            if code in added or code not in TAB_REGISTRY:
                continue
            title, cls = TAB_REGISTRY[code]
            try:
                self.tabs.addTab(cls(self.api), title)
                added.add(code)
            except Exception:
                continue
        if not added:  # на крайний случай
            self.tabs.addTab(ClientsTab(self.api), "Клиенты")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e2e8f0;")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("FitIntel Pro")
        title.setObjectName("header-title")
        h_layout.addWidget(title)
        h_layout.addStretch()

        role = self.user.get("role", "admin")
        role_name = getattr(role, "value", role)
        user_info = QLabel(f"{self.user.get('full_name', self.user.get('username', 'Админ'))} | {role_name}")
        user_info.setObjectName("header-user")
        h_layout.addWidget(user_info)
        h_layout.addSpacing(16)

        btn_logout = QPushButton("Выход")
        btn_logout.setObjectName("logout")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.clicked.connect(self._on_logout)
        h_layout.addWidget(btn_logout)
        layout.addWidget(header)

        self._build_tabs()
        layout.addWidget(self.tabs)

        self.status = QStatusBar()
        self.status.showMessage("Сервер подключён")
        self.setStatusBar(self.status)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        act_refresh = QAction("Обновить", self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self._refresh_current)
        file_menu.addAction(act_refresh)
        file_menu.addSeparator()
        act_exit = QAction("Выход", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    def _start_health_check(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_health)
        self.timer.start(10000)

    def _check_health(self):
        try:
            self.api.health()
            self.status.showMessage("Сервер подключён | FitIntel Pro v1.3.1")
        except Exception:
            self.status.showMessage("Сервер недоступен — проверьте бэкенд localhost:8001")

    def _refresh_current(self):
        widget = self.tabs.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Выход", "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.api.clear_token()
            self.logout_requested.emit()
            self.close()
