"""Диалог принудительной смены пароля при первом входе"""
import json, urllib.request
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QLabel, QMessageBox
)

class ChangePasswordDialog(QDialog):
    def __init__(self, api, token, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.setWindowTitle("Смена пароля — Обязательно")
        self.setMinimumWidth(350)
        self._build_ui()

    def _req(self, method, path, data=None):
        base = getattr(self.api, "base_url", "http://localhost:8001/api/v1")
        r = urllib.request.Request(
            base.rstrip("/") + path,
            data=json.dumps(data).encode() if data else None,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token
            },
            method=method
        )
        try:
            return json.load(urllib.request.urlopen(r, timeout=15))
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            try:
                err = json.loads(body)
                raise Exception(err.get("detail", str(e)))
            except Exception:
                raise Exception(body or str(e))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        warning = QLabel("Это ваш первый вход. Для безопасности смените пароль.")
        warning.setStyleSheet("color: #d97706; font-weight: 600; padding: 8px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        form = QFormLayout()
        self.ed_old = QLineEdit()
        self.ed_old.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_old.setPlaceholderText("Временный пароль из письма")
        form.addRow("Старый пароль:", self.ed_old)

        self.ed_new = QLineEdit()
        self.ed_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_new.setPlaceholderText("Новый пароль (мин. 8 символов)")
        form.addRow("Новый пароль:", self.ed_new)

        self.ed_confirm = QLineEdit()
        self.ed_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_confirm.setPlaceholderText("Повторите новый пароль")
        form.addRow("Подтверждение:", self.ed_confirm)
        layout.addLayout(form)

        btn = QPushButton("Сохранить и войти")
        btn.setStyleSheet("background: #059669; color: white; padding: 10px; font-weight: 600;")
        btn.clicked.connect(self._save)
        layout.addWidget(btn)

    def _save(self):
        old = self.ed_old.text()
        new = self.ed_new.text()
        confirm = self.ed_confirm.text()

        if len(new) < 8:
            QMessageBox.warning(self, "Ошибка", "Пароль минимум 8 символов")
            return
        if new != confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        try:
            self._req("POST", "/auth/change-password", {
                "current_password": old,
                "new_password": new
            })
            QMessageBox.information(self, "Готово", "Пароль изменён. Вход выполнен.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))