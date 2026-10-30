# -*- coding: utf-8 -*-
"""E69: Активация лицензии при первом запуске — до логина.
Только лицензионный ключ: логин/пароль извлекаются из payload ключа."""
import json
import base64 as b64
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton)
from PyQt6.QtCore import Qt


class ActivationDialog(QDialog):
    def __init__(self, api_base: str, parent=None, preset_key: str = ""):
        super().__init__(parent)
        self.api_base = api_base.rstrip("/")
        self.token = None
        self.user_data = None
        self.setWindowTitle("FitIntel Pro — Активация лицензии")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        title = QLabel("<b>Первый запуск системы.</b><br>"
                       "Введите лицензионный ключ из письма.<br>"
                       "Логин главного администратора: <b>SuperAdmin</b>, "
                       "пароль — тот, что указан в письме.")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setWordWrap(True)
        lay.addWidget(title)
        self.ed_key = QLineEdit()
        self.ed_key.setPlaceholderText("Лицензионный ключ (FIPRO-...)")
        if preset_key:
            self.ed_key.setText(preset_key)
        lay.addWidget(self.ed_key)
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
        if not key.startswith("FIPRO-"):
            self.lbl.setText("Ключ должен начинаться с FIPRO-")
            return
        # Логин и пароль — из payload ключа (подпись защищает от подделки)
        try:
            raw = key[len("FIPRO-"):].rsplit(".", 1)[0]
            payload = json.loads(b64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
            login = payload.get("superadmin_login") or "SuperAdmin"
            pw = payload.get("temp_password", "")
        except Exception:
            self.lbl.setText("Ключ повреждён при копировании — выделите поле целиком (Ctrl+A → Ctrl+C)")
            return
        if not pw:
            self.lbl.setText("В ключе нет пароля — сгенерируйте лицензию новой версией Studio")
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
        try:
            lr = self._post("/auth/login", {"login": login, "password": pw})
            self.token = lr.get("access_token")
            self.user_data = lr.get("user") or {"username": login}
            self.accept()
        except Exception:
            self.lbl.setText("Лицензия активирована ✅ Нажмите «У меня уже есть доступ» "
                             "и войдите с паролем из письма.")

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._activate()
        else:
            super().keyPressEvent(ev)