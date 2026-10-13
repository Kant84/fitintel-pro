#fitintel-desktop\main.py"
"""FitIntel Pro Desktop — Entry Point

Запуск:
    python main.py

Сборка .exe:
    build_exe.bat (pyinstaller onefile)
"""
import sys
import os
import json
from pathlib import Path
from PyQt6.QtGui import QIcon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app_logging import log, install_excepthook
from api import ApiClient
from windows import LoginWindow, MainWindow
from windows.startup_dialog import StartupDialog

from paths import APP_DIR, SETTINGS as _SETTINGS_PATH, CONNECTIONS as _CONN_PATH

ICON_PATH = APP_DIR / "assets" / "FitIntel_icon.ico"


def _auto_connect_if_single() -> dict | None:
    """Если профиль подключения ровно один — применить его без диалога.

    Возвращает cfg или None (тогда показываем StartupDialog).
    Чтобы вернуть диалог — добавьте второй профиль (экран «Подключения»).
    """
    conn_path = APP_DIR / "connections.json"
    if not conn_path.exists():
        return None  # файла нет — диалог сам создаст дефолтный профиль
    try:
        conns = json.loads(conn_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(conns, list) or len(conns) != 1:
        return None
    conn = conns[0]
    cfg_path = APP_DIR / "client_settings.json"
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["api_base"] = conn.get("web_url", "http://localhost:8001/api/v1")
    cfg["saved_login"] = conn.get("web_login", "")
    cfg["saved_password"] = conn.get("web_pass", "")
    try:
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not auto-save connection: %s", e)
    return cfg


def main():
    install_excepthook()

    # Windows: собственная иконка в панели задач (иначе показывает python.exe)
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FitIntel.Pro.Desktop")
    except Exception:
        pass

    log.info('=== FitIntel Pro Desktop запущен ===')
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Иконка приложения: заголовок окна, панель задач, Alt+Tab
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    else:
        log.warning("Иконка не найдена: %s", ICON_PATH)

    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Базовый URL из client_settings.json (если файл есть), иначе localhost по умолчанию
    try:
        if _SETTINGS_PATH.exists():
            _cfg = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            api = ApiClient(base_url=_cfg.get("api_base", "http://localhost:8001/api/v1"))
        else:
            api = ApiClient()
        log.info("API base (старт): %s", api.base_url)
    except Exception:
        api = ApiClient()

    # === E72: первый запуск — спросить адрес сервера (одна сборка на все клубы) ===
    try:
        _cfg = {}
        if _SETTINGS_PATH.exists():
            _cfg = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        _has_profiles = _CONN_PATH.exists()
        if not _cfg.get("api_base") and not _has_profiles:
            from PyQt6.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(
                None, "FitIntel Pro — Подключение к серверу",
                "Введите адрес сервера вашего клуба.\n\n"
                "Примеры:\n"
                "   http://192.168.0.10\n"
                "   http://fit.yourclub.ru\n\n"
                "Адрес сохранится на этом компьютере.",
                text="http://")
            if ok and url.strip():
                url = url.strip().rstrip("/")
                if not url.endswith("/api/v1"):
                    url += "/api/v1"
                _cfg["api_base"] = url
                _SETTINGS_PATH.write_text(json.dumps(_cfg, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
                # один профиль подключения — старый диалог базы не перекроет адрес
                _CONN_PATH.write_text(json.dumps([{
                    "name": "Сервер клуба",
                    "type": "web",
                    "web_url": url,
                    "web_login": "",
                    "web_pass": "",
                }], ensure_ascii=False, indent=2), encoding="utf-8")
                api.base_url = url
                log.info("E72: адрес сервера сохранён при первом запуске: %s", url)
    except Exception as e:
        log.warning("E72 first-run prompt skipped: %s", e)
    # ==============================================================================

    login = LoginWindow()
    main_window = None
    rfid_monitor = None

    def on_login_success(user_data: dict, token: str):
        log.info('Вход выполнен: %s', user_data.get('username', '?'))
        nonlocal main_window, rfid_monitor
        api.set_token(token)

        # Сохраняем токен в client_settings.json
        try:
            cfg_path = str(APP_DIR / "client_settings.json")
            cfg = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["token"] = token
            cfg["access_token"] = token
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            log.info("Token saved to client_settings.json")
        except Exception as e:
            log.warning("Could not save token: %s", e)

        # === Выбор базы: авто-подключение при единственном профиле ===
        auto_cfg = _auto_connect_if_single()
        if auto_cfg is None:
            startup = StartupDialog()
            if startup.exec() != QDialog.DialogCode.Accepted:
                log.info("Пользователь отменил выбор базы")
                show_login()
                return
        else:
            log.info("Авто-подключение к единственной базе: %s", auto_cfg.get("api_base"))
        # Перезагружаем api с актуальными настройками
        try:
            cfg_path = str(APP_DIR / "client_settings.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                api.base_url = cfg.get("api_base", api.base_url)
                log.info("API base updated to: %s", api.base_url)
        except Exception as e:
            log.warning("Could not reload API base: %s", e)
        # ==============================================

        main_window = MainWindow(api, user_data, token)
        main_window.logout_requested.connect(show_login)

        try:
            from rfid_monitor_widget import RFIDMonitorWidget, set_global_token
            rfid_monitor = RFIDMonitorWidget(parent=None)
            set_global_token(token)
            log.info('E16 RFID Monitor integrated')
        except Exception as e:
            log.error('E16 RFID Monitor FAIL: %s', e)

        main_window.show()

    def show_login():
        nonlocal rfid_monitor
        if rfid_monitor is not None:
            try:
                rfid_monitor.close()
                rfid_monitor.deleteLater()
            except Exception:
                pass
            rfid_monitor = None

        login.edit_pass.clear()
        login.lbl_status.setText("")
        login.btn_login.setEnabled(True)
        login.btn_login.setText("Войти")
        login.show()

    login.login_success.connect(on_login_success)

    # === E69: первый запуск — активация ДО показа окна входа ===
    activation_done = False
    try:
        import urllib.request
        req = urllib.request.Request(api.base_url + "/license/status")
        with urllib.request.urlopen(req, timeout=5) as r:
            _lic = json.loads(r.read().decode())
        if not _lic.get("activated"):
            from windows.activation_dialog import ActivationDialog
            dlg = ActivationDialog(api.base_url)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.token:
                login.hide()
                on_login_success(dlg.user_data or {"username": "SuperAdmin"}, dlg.token)
                activation_done = True
    except Exception as e:
        log.warning("E69 activation check skipped: %s", e)

    if not activation_done:
        login.show()
    # ============================================================

    code = app.exec()
    log.info('=== Клиент завершил работу ===')
    sys.exit(code)


if __name__ == "__main__":
    main()