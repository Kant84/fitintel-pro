"""FitIntel Pro — Main Window (боковое меню слева, темы, масштаб)"""
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QMessageBox, QFrame,
    QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont

from api import ApiClient
from windows import theme
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
from windows.schedule_tab import ScheduleTab
from windows.reports_tab import ReportsTab
from windows.documents_tab import DocumentsTab
from windows.roles_tab import RolesTab
from windows.setup_tab import SetupTab
from windows.tariffs_tab import TariffsTab

SETTINGS_PATH = Path(__file__).parents[1] / "client_settings.json"

TAB_REGISTRY = {
    "dashboard":     ("Главная", DashboardTab),
    "analytics":     ("Аналитика", DashboardTab),
    "clients":       ("Клиенты", ClientsTab),
    "subscriptions": ("Абонементы", SubscriptionsTab),
    "tariffs":       ("Тарифы", TariffsTab),
    "visits":        ("Входы/Выходы", VisitsTab),
    "schedule":      ("Расписание", ScheduleTab),
    "payments":      ("Платежи", PaymentsTab),
    "reports":       ("Отчёты", ReportsTab),
    "documents":     ("Документы", DocumentsTab),
    "users":         ("Пользователи", UsersTab),
    "roles":         ("Роли и права", RolesTab),
    "devices":       ("Устройства", DevicesTab),
    "face_id":       ("Face ID", FaceIDTab),
    "license":       ("Лицензия", LicenseTab),
    "ui_config":     ("Экраны ролей", UiConfigTab),
    "setup":         ("Мастер установки", SetupTab),
    "settings":      ("Настройки", SettingsTab),
}

DEFAULT_TABS = ["dashboard", "clients", "subscriptions", "tariffs", "visits",
                "schedule", "payments", "reports", "documents", "users", "roles",
                "devices", "face_id", "license", "ui_config", "setup", "settings"]

SIDEBAR_LIGHT = """
    QListWidget { background: #ffffff; border: none; border-right: 1px solid #e2e8f0; outline: none; }
    QListWidget::item { padding: 10px 14px; color: #475569; font-weight: 600; border-left: 3px solid transparent; }
    QListWidget::item:selected { background: #ecfdf5; color: #065f46; border-left: 3px solid #10b981; }
    QListWidget::item:hover:!selected { background: #f1f5f9; }
"""
SIDEBAR_DARK = """
    QListWidget { background: #1e293b; border: none; border-right: 1px solid #334155; outline: none; }
    QListWidget::item { padding: 10px 14px; color: #94a3b8; font-weight: 600; border-left: 3px solid transparent; }
    QListWidget::item:selected { background: #064e3b; color: #a7f3d0; border-left: 3px solid #10b981; }
    QListWidget::item:hover:!selected { background: #334155; }
"""


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, api: ApiClient, user_data: dict, token: str):
        super().__init__()
        self.api = api
        self.user = user_data
        self.token = token
        self.ui_settings = self._load_ui_settings()
        self.setWindowTitle("FitIntel Pro — Система управления [sidebar v2]")
        self.setMinimumSize(1280, 800)
        self._build_ui()
        self.apply_appearance(save=False)
        self._start_health_check()

    def _load_ui_settings(self) -> dict:
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"theme": "light", "font_size": 10}

    def apply_appearance(self, theme_name: str = None, font_size: int = None, save: bool = True):
        old_theme = self.ui_settings.get("theme", "light")
        if theme_name:
            self.ui_settings["theme"] = theme_name
        if font_size:
            self.ui_settings["font_size"] = max(8, min(18, int(font_size)))
        cur_theme = self.ui_settings.get("theme", "light")
        size = self.ui_settings.get("font_size", 10)

        QApplication.instance().setFont(QFont("Segoe UI", size))
        dark = cur_theme == "dark"
        theme.set_dark(dark)

        sidebar = SIDEBAR_DARK if dark else SIDEBAR_LIGHT
        if dark:
            self._header_bg = "background: #1e293b; border-bottom: 1px solid #334155;"
            self.setStyleSheet(
                "QMainWindow { background-color: #0f172a; }" + sidebar +
                "QStackedWidget { background: #0f172a; }" +
                "QLabel#header-title { font-size: 20px; font-weight: 700; color: #f1f5f9; }"
                "QLabel#header-user { font-size: 12px; color: #94a3b8; }"
                "QStatusBar { background: #1e293b; color: #94a3b8; font-size: 12px; border-top: 1px solid #334155; }"
                "QMenuBar { background: #0f172a; color: #cbd5e1; } QMenuBar::item:selected { background: #334155; }"
                "QMenu { background: #1e293b; color: #cbd5e1; } QMenu::item:selected { background: #334155; }"
                "QPushButton#logout { background: transparent; color: #f87171; border: 1px solid #f87171; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; }"
                "QPushButton#logout:hover { background: #f87171; color: #0f172a; }")
        else:
            self._header_bg = "background: #ffffff; border-bottom: 1px solid #e2e8f0;"
            self.setStyleSheet(
                "QMainWindow { background-color: #f1f5f9; }" + sidebar +
                "QLabel#header-title { font-size: 20px; font-weight: 700; color: #0f172a; }"
                "QLabel#header-user { font-size: 12px; color: #64748b; }"
                "QStatusBar { background: #ffffff; color: #64748b; font-size: 12px; border-top: 1px solid #e2e8f0; }"
                "QPushButton#logout { background: transparent; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; }"
                "QPushButton#logout:hover { background: #ef4444; color: white; }")

        if hasattr(self, "_header"):
            self._header.setStyleSheet(self._header_bg)
        if save:
            try:
                SETTINGS_PATH.write_text(json.dumps(self.ui_settings, ensure_ascii=False),
                                         encoding="utf-8")
            except Exception:
                pass
        if theme_name and theme_name != old_theme and hasattr(self, "stack"):
            self._rebuild_content()

    def zoom_in(self):
        self.apply_appearance(font_size=self.ui_settings.get("font_size", 10) + 1)

    def zoom_out(self):
        self.apply_appearance(font_size=self.ui_settings.get("font_size", 10) - 1)

    def _visible_screen_codes(self) -> list:
        try:
            data = self.api.get_ui_my()
            codes = [s["code"] for s in data.get("screens", [])]
            if codes:
                return codes
        except Exception:
            pass
        return list(DEFAULT_TABS)

    def _make_widget(self, code: str):
        cls = TAB_REGISTRY[code][1]
        if code == "settings":
            return SettingsTab(self.api, self)
        return cls(self.api)

    def _rebuild_content(self):
        current = self.sidebar.currentRow()
        self.sidebar.blockSignals(True)
        self.sidebar.clear()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        added = set()
        for code in self._visible_screen_codes():
            if code in added or code not in TAB_REGISTRY:
                continue
            try:
                widget = self._make_widget(code)
            except Exception:
                continue
            widget.setStyleSheet(theme.widget_style())
            title = TAB_REGISTRY[code][0]
            item = QListWidgetItem(title)
            item.setSizeHint(QSize(-1, 38))
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.sidebar.addItem(item)
            self.stack.addWidget(widget)
            added.add(code)

        if self.sidebar.count() == 0:
            self.sidebar.addItem(QListWidgetItem("Клиенты"))
            self.stack.addWidget(ClientsTab(self.api))

        self.sidebar.blockSignals(False)
        row = current if 0 <= current < self.sidebar.count() else 0
        self.sidebar.setCurrentRow(row)
        self.stack.setCurrentIndex(row)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QFrame()
        self._header.setFixedHeight(64)
        h_layout = QHBoxLayout(self._header)
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
        layout.addWidget(self._header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.currentRowChanged.connect(self._on_nav)
        body.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)

        self._rebuild_content()

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

        view_menu = menubar.addMenu("Вид")
        act_light = QAction("Светлая тема", self)
        act_light.triggered.connect(lambda: self.apply_appearance(theme_name="light"))
        view_menu.addAction(act_light)
        act_dark = QAction("Тёмная тема", self)
        act_dark.triggered.connect(lambda: self.apply_appearance(theme_name="dark"))
        view_menu.addAction(act_dark)
        view_menu.addSeparator()
        act_zi = QAction("Увеличить шрифт", self)
        act_zi.setShortcut("Ctrl++")
        act_zi.triggered.connect(self.zoom_in)
        view_menu.addAction(act_zi)
        act_zo = QAction("Уменьшить шрифт", self)
        act_zo.setShortcut("Ctrl+-")
        act_zo.triggered.connect(self.zoom_out)
        view_menu.addAction(act_zo)

    def _on_nav(self, row: int):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

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
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            widget = self.stack.currentWidget()
            if hasattr(widget, "refresh"):
                widget.refresh()
        finally:
            QApplication.restoreOverrideCursor()

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Выход", "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.api.clear_token()
            self.logout_requested.emit()
            self.close()


# ============================ E56_WIRED ============================
try:
    from windows.integrations_tab import IntegrationsTab
    from windows.messenger_tab import MessengerTab
    TAB_REGISTRY["integrations"] = ("Интеграции", IntegrationsTab)
    TAB_REGISTRY["messenger"] = ("MAX сообщения", MessengerTab)
except Exception as _e:
    print("E56 tabs:", _e)

try:
    _e56_orig_init = MainWindow.__init__
    def _e56_mw_init(self, *a, **kw):
        _e56_orig_init(self, *a, **kw)
        try:
            from windows.help_dialog import install_help
            install_help(self)
        except Exception as _e2:
            print("help install:", _e2)
    MainWindow.__init__ = _e56_mw_init
except Exception as _e3:
    print("E56 wire:", _e3)
# ========================== E56_WIRED END ==========================


# ============================ E58_WIRED ============================
try:
    from windows.notifications_tab import NotificationsTab
    TAB_REGISTRY["notifications"] = ("Оповещения", NotificationsTab)
except Exception as _e58:
    print("E58 tab:", _e58)
# ========================== E58_WIRED END ==========================


# === E59D_WIRED: theme toggle in menu ===
try:
    from windows import theme as _th59
    _orig_mw_init_59d = MainWindow.__init__
    def _mw_init_59d(self, *a, **kw):
        _orig_mw_init_59d(self, *a, **kw)
        try:
            from PyQt6.QtGui import QAction
            act = QAction("🌗 Переключить тему", self)
            act.triggered.connect(lambda: _th59.set_dark(not _th59.DARK))
            mb = self.menuBar()
            view = None
            for a in mb.actions():
                if a.text().strip().lower().startswith("вид"):
                    view = a.menu()
                    break
            if view is None:
                view = mb.addMenu("Вид")
            view.addAction(act)
        except Exception as e:
            print("theme toggle menu:", e)
    MainWindow.__init__ = _mw_init_59d
    print("E59D theme toggle OK")
except Exception as e:
    print("E59D FAIL:", e)


# === E61_WIRED: AI Center tab ===
try:
    from windows.ai_center_tab import AICenterTab
    if "ai_center" not in TAB_REGISTRY:
        TAB_REGISTRY["ai_center"] = ("AI Центр", AICenterTab)
        print("E61 AI tab OK")
except Exception as e:
    print("E61 FAIL:", e)

# === E17_NOTIFY_WIRED ===
try:
    from windows.notifications_tab import NotificationsTab
    TAB_REGISTRY["notifications"] = ("🔔 Уведомления", NotificationsTab)
    print("[E17] вкладка Уведомления зарегистрирована")
except Exception as _e17e:
    print("[E17] wire FAIL:", _e17e)


# === E18_COMMERCE_WIRED ===
try:
    from windows.commerce_tab import CommerceTab
    TAB_REGISTRY["commerce"] = ("🏢 Коммерция", CommerceTab)
    print("E18 commerce tab OK")
except Exception as _e18ui:
    print("E18 commerce tab FAIL:", _e18ui)
