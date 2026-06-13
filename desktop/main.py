import sys
from PyQt6.QtWidgets import QApplication, QDialog
from api.client import ApiClient
from windows import LoginWindow, MainWindow

if __name__ == "__main__":
    api = ApiClient()
    app = QApplication(sys.argv)

    login = LoginWindow(api)
    if login.exec() == QDialog.DialogCode.Accepted:
        user = login.user_info
        token = login.token
        window = MainWindow(api, user, token)
        window.show()
        sys.exit(app.exec())
