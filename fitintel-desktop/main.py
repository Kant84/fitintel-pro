from windows.credentials_tab import CredentialsTab
"""FitIntel Pro Desktop — Entry Point

Запуск:
    python main.py

Сборка .exe:
    python build.py
"""
import sys
import os

# Добавляем путь к текущей директории для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app_logging import log, install_excepthook
from api import ApiClient
from windows import LoginWindow, MainWindow


def main():
    install_excepthook()
    log.info('=== FitIntel Pro Desktop запущен ===')
    # Включаем поддержку высокого DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Глобальный шрифт
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    api = ApiClient()

    login = LoginWindow()
    main_window = None

    def on_login_success(user_data: dict, token: str):
        log.info('Вход выполнен: %s', user_data.get('username', '?'))
        nonlocal main_window
        api.set_token(token)
        main_window = MainWindow(api, user_data, token)
        
        # === E16: RFID Monitor (всплывает при считывании браслета) ===
        try:
            from rfid_monitor_widget import RFIDMonitorWidget
            main_window.rfid_monitor = RFIDMonitorWidget()  # без parent — независимое окно
            print('E16 RFID Monitor integrated')
        except Exception as e:
            print('E16 RFID Monitor FAIL:', e)
        
        main_window.logout_requested.connect(show_login)
        main_window.show()

    def show_login():
        login.edit_pass.clear()
        login.lbl_status.setText("")
        login.btn_login.setEnabled(True)
        login.btn_login.setText("Войти")
        login.show()

    login.login_success.connect(on_login_success)
    login.show()

    code = app.exec()
    log.info('=== Клиент завершил работу ===')
    sys.exit(code)


if __name__ == "__main__":
    main()



