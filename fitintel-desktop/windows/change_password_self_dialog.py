# -*- coding: utf-8 -*-
"""Добровольная смена СВОЕГО пароля (self-service).
Та же механика, что при временном пароле: POST /auth/change-password."""
import json, urllib.request
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox
)


class ChangePasswordSelfDialog(QDialog):
    def __init__(self, api, token, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.setWindowTitle("🔑 Смена пароля")
        self.setMinimumWidth(380)
        self._build_ui()

    def _req(self, path, data):
        base = getattr(self.api, "base_url", "http://localhost:8001/api/v1")
        req = urllib.request.Request(
            base.rstrip("/") + path,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.token})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            try:
                raise Exception(json.loads(body).get("detail", body))
            except json.JSONDecodeError:
                raise Exception(body or str(e))

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        hint = QLabel("Рекомендуем менять пароль регулярно и не использовать "
                      "один пароль на нескольких сервисах.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b; padding: 4px;")
        lay.addWidget(hint)
        form = QFormLayout()
        self.ed_old = QLineEdit(); self.ed_old.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_old.setPlaceholderText("Текущий пароль")
        form.addRow("Текущий пароль:", self.ed_old)
        self.ed_new = QLineEdit(); self.ed_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_new.setPlaceholderText("Новый пароль (мин. 8 символов)")
        form.addRow("Новый пароль:", self.ed_new)
        self.ed_new2 = QLineEdit(); self.ed_new2.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_new2.setPlaceholderText("Повторите новый пароль")
        form.addRow("Подтверждение:", self.ed_new2)
        lay.addLayout(form)
        btn = QPushButton("💾 Сохранить")
        btn.setStyleSheet("background: #059669; color: white; padding: 10px; font-weight: 600;")
        btn.clicked.connect(self._save)
        lay.addWidget(btn)

    def _save(self):
        old = self.ed_old.text()
        new = self.ed_new.text()
        if len(new) < 8:
            QMessageBox.warning(self, "Пароль", "Новый пароль должен быть не короче 8 символов.")
            return
        if new != self.ed_new2.text():
            QMessageBox.warning(self, "Пароль", "Новые пароли не совпадают.")
            return
        try:
            self._req("/auth/change-password",
                      {"current_password": old, "new_password": new})
        except Exception as e:
            QMessageBox.warning(self, "Смена пароля",
                                "Не удалось сменить пароль: %s" % e)
            return
        QMessageBox.information(self, "Готово",
                                "Пароль успешно изменён. При следующем входе используйте новый.")
        self.accept()
