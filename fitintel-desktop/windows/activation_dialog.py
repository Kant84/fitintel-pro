# -*- coding: utf-8 -*-
"""E69: Активация лицензии при первом запуске — до логина.
Клиент вводит ключ + пароль из письма → activate (без токена) → автовход."""
import json
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton)
from PyQt6.QtCore import Qt


class ActivationDialog(QDialog):
    def __init__(self, api_base: str, parent=None):
        super().__init__(parent)
        self.api_base = api_base.rstrip("/")
        self.token = None
        self.user_data = None
        self.setWindowTitle("FitIntel Pro — Активация лицензии")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        title = QLabel("<b>Первый запуск системы.</b><br>"
                       "Введите данные из письма с лицензией.<br>"
                       "Логин главного администратора: <b>SuperAdmin</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setWordWrap(True)
        lay.addWidget(title)
        self.ed_key = QLineEdit()
        self.ed_key.setPlaceholderText("Лицензионный ключ (FIPRO-...)")
        lay.addWidget(self.ed_key)
        self.ed_pass = QLineEdit()
        self.ed_pass.setPlaceholderText("Пароль из письма")
        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self.ed_pass)
        row = QHBoxLayout()
        b_act = QPushButton("Активировать и войти")
        b_act.setStyleSheet(
            "QPushButton { background: #059669; color: white; border: none;"
            " border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        b_act.clicked.connect(self._activate)
        b_skip = QPushButton("У меня уже есть доступ")
        b_skip.clicked.connect(self.reject)
        row.addWidget(b_act)
        row.addWidget(b_skip)
        lay.addLayout(row)
        self.lbl = QLabel("")
        self.lbl.setStyleSheet("color: #b91c1c;")
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)

    def _post(self, path, payload, token=None):
        req = urllib.request.Request(
            self.api_base + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    def _activate(self):
        key = self.ed_key.text().strip()
        pw = self.ed_pass.text().strip()
        if not key.startswith("FIPRO-"):
            self.lbl.setText("Ключ должен начинаться с FIPRO-")
            return
        if len(pw) < 6:
            self.lbl.setText("Введите пароль из письма")
            return
        try:
            r = self._post("/license/activate", {"key": key})
        except urllib.error.HTTPError as e:
            self.lbl.setText(f"Сервер отклонил: {e.code}")
            return
        except Exception as e:
            self.lbl.setText(f"Нет связи с сервером: {e}")
            return
        if not r.get("activated"):
            self.lbl.setText("Ключ не принят: " + str(r.get("reason", r))[:180])
            return
        # Активация прошла → сервер уже установил пароль из ключа.
        # Входим под SuperAdmin с паролем из письма.
        login = r.get("superadmin_login") or "SuperAdmin"
        try:
            lr = self._post("/auth/login", {"login": login, "password": pw})
            self.token = lr.get("access_token")
            self.user_data = lr.get("user") or {"username": login}
            self.accept()
        except Exception as e:
            self.lbl.setText("Лицензия активирована ✅ Нажмите «У меня уже есть доступ» "
                             "и войдите: SuperAdmin / пароль из письма.")

    # Enter в полях = активация
    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._activate()
        else:
            super().keyPressEvent(ev)