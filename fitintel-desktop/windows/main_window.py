"""FitIntel Pro — Main Window (боковое меню слева, темы, масштаб, ленивая загрузка вкладок)"""
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
from windows.connections_tab import ConnectionsTab
from windows import theme
from windows.icons import icon as _icon, polish as _polish
from windows.clients_tab import ClientsTab
from windows.subscriptions_tab import SubscriptionsTab
from windows.visits_tab import VisitsTab
from windows.face_id_tab import FaceIDTab
from windows.license_tab import LicenseTab
from windows.settings_tab import SettingsTab
from windows.dashboard_tab import DashboardTab
from windows.payments_tab import PaymentsTab
from windows.music_tab import MusicTab
from windows.users_tab import UsersTab
from windows.devices_tab import DevicesTab
from windows.ui_config_tab import UiConfigTab
from windows.schedule_tab import ScheduleTab
from windows.services_tab import ServicesTab, ShopTab
from windows.reports_tab import ReportsTab
from windows.documents_tab import DocumentsTab
from windows.roles_tab import RolesTab
from windows.setup_tab import SetupTab
from windows.tariffs_tab import TariffsTab

from paths import SETTINGS as SETTINGS_PATH

TAB_REGISTRY = {
    "dashboard":     ("Главная", DashboardTab),
    "clients":       ("Клиенты", ClientsTab),
    "subscriptions": ("Абонементы", SubscriptionsTab),
    "services":      ("Услуги", ServicesTab),
    "visits":        ("Входы/Выходы", VisitsTab),
    "schedule":      ("Расписание", ScheduleTab),
    "music":         (" Музыка/DJ", MusicTab),
    "users":         ("Пользователи", UsersTab),
    "face_id":       ("Face ID", FaceIDTab),
    "settings":      ("Настройки", SettingsTab),
    "connections":   ("Подключения", ConnectionsTab),
    # хабы: класс-заглушка, реальное построение — в MainWindow._make_widget
    "accounting":    ("Бухгалтерия", QWidget),
    "ai_center":     ("AI центр", QWidget),
    "shop":          ("Магазин", ShopTab),
}

DEFAULT_TABS = ["dashboard", "clients", "subscriptions", "tariffs", "visits", "services",
                "schedule", "payments", "music", "reports", "documents", "users", "roles",
                "devices", "face_id", "license", "ui_config", "setup", "settings", "credentials", "connections"]

SIDEBAR_LIGHT = """
    QListWidget { background: #FFFDF2; border: none; border-right: 1px solid #4338ca; outline: none; }
    QListWidget::item { padding: 10px 14px; color: #475569; font-weight: 600; border-left: 3px solid transparent; }
    QListWidget::item:selected { background: #E4D7A8; color: #1a1a2e; border-left: 3px solid #4338ca; }
    QListWidget::item:hover:!selected { background: #F1E8C4; }
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
        from pathlib import Path as _Path
        from PyQt6.QtGui import QIcon as _QIcon
        _icon = _Path(__file__).parents[1] / "assets" / "FitIntel_icon.ico"
        if _icon.exists():
            self.setWindowIcon(_QIcon(str(_icon)))
        self.api = api
        self.user = user_data
        self.token = token
        self._built = {}   # code -> widget (построенные вкладки)
        self._codes = []   # row -> code
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
            self._header_bg = "background: #FFFDF2; border-bottom: 1px solid #4338ca;"
            self.setStyleSheet(
                "QMainWindow { background-color: #F9F3D7; }" + sidebar +
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
                # служебные вкладки — только у суперадмина
                if str(self.user.get("username", "")).lower() == "superadmin":
                    for extra in ("credentials", "connections", "services"):
                        if extra not in codes:
                            codes.append(extra)
                    if "music" not in codes:      # <-- добавить
                        codes.append("music")     # <-- добавить
                return codes
        except Exception:
            pass
        # fail-closed: при ошибке или пустой матрице — только Главная
        return ["dashboard"]

    def _make_widget(self, code: str):
        if code == "settings":
            from windows.settings_hub_tab import SettingsHubTab
            return SettingsHubTab(self.api, self)
        if code == "accounting":
            from windows.finance_hub_tab import FinanceHubTab
            return FinanceHubTab(self.api)
        if code == "ai_center":
            from windows.ai_hub_tab import AIHubTab
            return AIHubTab(self.api)
        cls = TAB_REGISTRY[code][1]
        return cls(self.api)

    def _build_tab(self, code: str):
        """Ленивое создание вкладки: заменяет placeholder в stack (строится один раз)."""
        if code in self._built:
            return self._built[code]
        row = self._codes.index(code)
        placeholder = self.stack.widget(row)
        try:
            widget = self._make_widget(code)
        except Exception as e:
            print("TAB BUILD FAIL:", code, "->", e)
            widget = QLabel("Не удалось загрузить экран: " + code)
        
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()
        self.stack.insertWidget(row, widget)
        try:
            _polish(widget)   # W5: эмодзи -> неон-иконки во всей вкладке
        except Exception as _pe:
            print("polish:", code, _pe)
        self._built[code] = widget
        return widget

    def _rebuild_content(self):
        current = self.sidebar.currentRow()
        self.sidebar.blockSignals(True)
        self.sidebar.clear()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self._built = {}
        self._codes = []

        added = set()
        for code in self._visible_screen_codes():
            if code in added or code not in TAB_REGISTRY:
                continue
            title = TAB_REGISTRY[code][0]
            item = QListWidgetItem(title)
            item.setIcon(_icon(code))
            item.setSizeHint(QSize(-1, 38))
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.sidebar.addItem(item)
            self.stack.addWidget(QWidget())  # placeholder: вкладка создастся при первом клике
            self._codes.append(code)
            added.add(code)

        if self.sidebar.count() == 0:
            self.sidebar.addItem(QListWidgetItem("Клиенты"))
            w = ClientsTab(self.api)
            #w.setStyleSheet(theme.widget_style())
            self.stack.addWidget(w)
            self._codes.append("clients")
            self._built["clients"] = w

        self.sidebar.blockSignals(False)
        row = current if 0 <= current < self.sidebar.count() else 0
        self.sidebar.setCurrentRow(row)
        self._on_nav(row)  # построить первую (текущую) вкладку сразу

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
        self.sidebar.setIconSize(QSize(20, 20))
        self.sidebar.setFixedWidth(200)
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
        act_clock = QAction(" Табло с часами (полный экран)", self)
        act_clock.setShortcut("F11")
        act_clock.setToolTip("Полноэкранные часы для ресепшена/входа. Esc — выход.")
        act_clock.triggered.connect(self._open_clock_board)
        view_menu.addAction(act_clock)
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
        if not (0 <= row < len(self._codes)):
            return
        code = self._codes[row]
        if code not in self._built:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self._build_tab(code)
            finally:
                QApplication.restoreOverrideCursor()
        self.stack.setCurrentIndex(row)

    def _start_health_check(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_health)
        self.timer.start(10000)

    def _check_health(self):
        try:
            self.api.health()
            self.status.showMessage("Сервер подключён | FitIntel Pro v1.6.1")
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

    
    def _open_clock_board(self):
        try:
            old = getattr(self, "_clock_board", None)
            if old is not None:
                try:
                    print("[DEBUG] clock: повторное F11 -> закрываем табло")
                    old.close()
                except Exception as e:
                    print("[DEBUG] clock: ошибка закрытия:", e)
                self._clock_board = None
                return
            from windows.clock_board import ClockBoardDialog
            club = str(self.user.get("club_name", "") or "")
            dlg = ClockBoardDialog(self, club_name=club)
            self._clock_board = dlg
            dlg.finished.connect(lambda _r: setattr(self, "_clock_board", None))
            print("[DEBUG] clock: табло открыто:", dlg)
            dlg.show()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Табло", str(e)[:150])


# ============================ E56_WIRED ============================
try:
    from windows.integrations_tab import IntegrationsTab
    from windows.messenger_tab import MessengerTab
    # [W5] «Интеграции» — подвкладка хаба «Настройки»; messenger остаётся отдельным
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
            act = QAction(" Переключить тему", self)
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
    TAB_REGISTRY["notifications"] = (" Уведомления", NotificationsTab)
    print("[E17] вкладка Уведомления зарегистрирована")
except Exception as _e17e:
    print("[E17] wire FAIL:", _e17e)


# [W5] commerce/export/accounting/integrations объединены в хабы — E-блоки отключены
# [W5] «Интеграции» — подвкладка хаба «Настройки»
except Exception as _e21ui:
    print("E21 integrations tab FAIL:", _e21ui)


# === E15_CREDENTIALS_TAB ===
try:
    from windows.credentials_tab import CredentialsTab
    TAB_REGISTRY["credentials"] = (" Браслеты/Карты", CredentialsTab)
    print("E15 credentials tab OK")
except Exception as _e15ui:
    print("E15 credentials tab FAIL:", _e15ui)
    
# === E71_AUDIT_TAB ===
try:
    from windows.audit_tab import AuditTab
    if "audit" not in TAB_REGISTRY:
        TAB_REGISTRY["audit"] = ("История", AuditTab)
        print("E71 audit tab OK")
except Exception as _e71:
    print("E71 audit tab FAIL:", _e71)


# === SELF PASSWORD CHANGE: пункт меню «Файл» ===
try:
    from windows.change_password_self_dialog import ChangePasswordSelfDialog
    _orig_init_pw = MainWindow.__init__
    def _mw_init_pw(self, *a, **kw):
        _orig_init_pw(self, *a, **kw)
        try:
            from PyQt6.QtGui import QAction
            act = QAction(" Сменить пароль…", self)
            act.setToolTip("Смена своего пароля (self-service)")
            act.triggered.connect(
                lambda: ChangePasswordSelfDialog(self.api, self.token, self).exec())
            for a_ in self.menuBar().actions():
                if a_.text().strip().lower().startswith("файл"):
                    a_.menu().addAction(act)
                    break
        except Exception as e:
            print("pwd change menu:", e)
    MainWindow.__init__ = _mw_init_pw
    print("Self password change OK")
except Exception as e:
    print("Self password change FAIL:", e)
    
# [W5] «Параметры клуба» — подвкладка хаба «Настройки»
except Exception as _w5t:
    print("W5 club_params tab FAIL:", _w5t)    

# === W5: табло с часами в меню «Файл» ===
try:
    from PyQt6.QtGui import QAction as _ActClk
    _orig_init_clk = MainWindow.__init__
    def _mw_init_clk(self, *a, **kw):
        _orig_init_clk(self, *a, **kw)
        try:
            act = _ActClk(" Табло с часами (F11)", self)
            act.triggered.connect(self._open_clock_board)
            for a_ in self.menuBar().actions():
                if a_.text().strip().lower().startswith("файл"):
                    a_.menu().addAction(act)
                    break
        except Exception as _e:
            print("clock menu:", _e)
    MainWindow.__init__ = _mw_init_clk
except Exception as _e:
    print("clock menu FAIL:", _e)

# ============================ W10: попап «Возврат клиентов» ============================
try:
    import os as _wos, json as _wjson, time as _wtime
    from PyQt6.QtWidgets import (QDialog as _wQD, QVBoxLayout as _wQV, QHBoxLayout as _wQH,
        QLabel as _wQL, QPushButton as _wQB, QListWidget as _wQLW, QListWidgetItem as _wQLWI)
    from PyQt6.QtCore import QTimer as _wQT

    _SNZ_PATH = _wos.path.join(_wos.path.dirname(__file__), "..", "return_snooze.json")

    def _snz_load():
        try:
            return _wjson.load(open(_SNZ_PATH, encoding="utf-8"))
        except Exception:
            return {}

    def _snz_save(key, days=0, hours=0):
        d = _snz_load()
        d[str(key)] = _wtime.time() + days * 86400 + hours * 3600
        try:
            _wjson.dump(d, open(_SNZ_PATH, "w", encoding="utf-8"))
        except Exception:
            pass

    class _ReturnClientsPopup(_wQD):
        def __init__(self, mw, clients):
            super().__init__(mw)
            self.mw = mw
            self.setWindowTitle("Возврат клиентов")
            self.setModal(False)
            self.resize(430, 330)
            v = _wQV(self)
            v.addWidget(_wQL("Эти клиенты давно не были в клубе. "
                             "«Забыть» — не напоминать про этого 30 дней."))
            self.listw = _wQLW()
            for c in clients:
                it = _wQLWI("%s  —  %s дн. без визита" % (c.get("name"), c.get("days")))
                it.setData(0x0100, c.get("client_id"))
                self.listw.addItem(it)
            v.addWidget(self.listw, 1)
            row = _wQH()
            b1 = _wQB(" Написать в MAX"); b1.clicked.connect(self._write)
            b2 = _wQB(" Забыть (30 дн)"); b2.clicked.connect(self._forget)
            b3 = _wQB(" Отложить на 3 часа"); b3.clicked.connect(self._snooze)
            b4 = _wQB(" Закрыть"); b4.clicked.connect(self.close)
            for b in (b1, b2, b3, b4):
                row.addWidget(b)
            v.addLayout(row)

        def _write(self):
            lw = self.mw.findChild(_wQLW)
            if lw is not None:
                for i in range(lw.count()):
                    if "MAX" in lw.item(i).text():
                        lw.setCurrentRow(i)
                        break
            self.close()

        def _forget(self):
            it = self.listw.currentItem()
            if it is None:
                return
            _snz_save(it.data(0x0100), days=30)
            self.listw.takeItem(self.listw.row(it))
            if not self.listw.count():
                self.close()

        def _snooze(self):
            _snz_save("__all__", hours=3)
            self.close()

    def _return_check(mw):
        try:
            d = _snz_load()
            if d.get("__all__", 0) > _wtime.time():
                return
            if getattr(mw, "_return_popup", None) is not None:
                return
            days = 14
            try:
                s = mw.api.session.get(mw.api._url("/messenger/settings"), timeout=10).json()
                days = int(s.get("inactive_days") or 14)
            except Exception:
                pass
            r = mw.api.session.get(mw.api._url("/analytics/inactive-clients"),
                                   params={"days": days}, timeout=20)
            r.raise_for_status()
            clients = [c for c in r.json().get("clients", [])
                       if d.get(str(c.get("client_id")), 0) < _wtime.time()]
            if clients:
                mw._return_popup = _ReturnClientsPopup(mw, clients)
                mw._return_popup.finished.connect(lambda _r: setattr(mw, "_return_popup", None))
                mw._return_popup.show()
        except Exception as e:
            print("return check:", str(e)[:120])

    _orig_init_w10 = MainWindow.__init__
    def _mw_init_w10(self, *a, **kw):
        _orig_init_w10(self, *a, **kw)
        try:
            t = _wQT(self)
            t.timeout.connect(lambda: _return_check(self))
            t.start(15 * 60 * 1000)
            _wQT.singleShot(30000, lambda: _return_check(self))
        except Exception as e:
            print("W10 popup:", e)
    MainWindow.__init__ = _mw_init_w10
    print("W10 return-clients popup OK")
except Exception as _w10e:
    print("W10 FAIL:", _w10e)
# ========================== W10 END ==========================

# === W13: колесо мыши скроллит QScrollArea под курсором (вкладки/окна) ===
try:
    from PyQt6.QtCore import QObject as _QO, QEvent as _QE
    from PyQt6.QtWidgets import QApplication as _QA, QScrollArea as _QSA

    class _WheelToScrollArea(_QO):
        def eventFilter(self, obj, ev):
            try:
                if ev.type() == _QE.Type.Wheel:
                    w = _QA.widgetAt(ev.globalPosition().toPoint())
                    sa = w
                    while sa is not None and not isinstance(sa, _QSA):
                        sa = sa.parentWidget()
                    if sa is not None:
                        sb = sa.verticalScrollBar()
                        if sb is not None and sb.maximum() > 0:
                            sb.setValue(sb.value() - int(ev.angleDelta().y() / 3))
                            return True
            except Exception:
                pass
            return False

    _WHEEL_FILTER = _WheelToScrollArea()
    _QA.instance().installEventFilter(_WHEEL_FILTER)
    print("W13 wheel-scroll OK")
except Exception as _e13w:
    print("W13 wheel-scroll FAIL:", _e13w)

# === W13-v2: колесо скроллит QScrollArea под курсором (гарантированная установка) ===
try:
    from PyQt6.QtCore import QObject as _QO2, QEvent as _QE2
    from PyQt6.QtWidgets import QApplication as _QA2, QScrollArea as _QSA2

    class _WheelToScrollAreaV2(_QO2):
        def eventFilter(self, obj, ev):
            try:
                if ev.type() == _QE2.Type.Wheel:
                    w = _QA2.widgetAt(ev.globalPosition().toPoint())
                    sa = w
                    while sa is not None and not isinstance(sa, _QSA2):
                        sa = sa.parentWidget()
                    if sa is not None and sa.isVisible():
                        sb = sa.verticalScrollBar()
                        if sb is not None and sb.maximum() > 0:
                            sb.setValue(sb.value() - int(ev.angleDelta().y() / 3))
                            return True
            except Exception:
                pass
            return False

    _WF2 = _WheelToScrollAreaV2()
    _orig_init_wheel2 = MainWindow.__init__
    def _init_wheel2(self, *a, **k):
        _orig_init_wheel2(self, *a, **k)
        try:
            _QA2.instance().installEventFilter(_WF2)
            print("W13 wheel v2 OK")
        except Exception as _e:
            print("W13 wheel v2 install:", _e)
    MainWindow.__init__ = _init_wheel2
except Exception as _e13w2:
    print("W13 wheel v2 FAIL:", _e13w2)