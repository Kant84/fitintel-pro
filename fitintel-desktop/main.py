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

from api import ApiClient
from windows import LoginWindow, MainWindow


def main():
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
        nonlocal main_window
        api.set_token(token)
        main_window = MainWindow(api, user_data, token)
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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
