# -*- coding: utf-8 -*-
"""П1: «Поддержка разработчика (email)» — окно КЛУБА.
Клуб пишет обращение -> письмо уходит С ящика КЛУБА (его SMTP: сервер/ящик/пароль)
НА support@fixintel.ru. Адрес получателя зашит на сервере, в desktop его нет."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QTextEdit,
                             QMessageBox, QApplication)
from PyQt6.QtCore import Qt


class SupportDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Поддержка разработчика (email)")
        self.resize(860, 620)
        v = QVBoxLayout(self)

        grp = QHBoxLayout()
        self.ed_host = QLineEdit()
        self.ed_host.setPlaceholderText("Почтовый сервер клиента, с доменом (напр. smtp.fixintel.ru)")
        self.ed_host.setMinimumWidth(280)
        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("Почтовый ящик клиента")
        self.ed_user.setMinimumWidth(210)
        self.ed_pass = QLineEdit()
        self.ed_pass.setPlaceholderText("Пароль")
        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pass.setMinimumWidth(140)
        bsave = QPushButton(" Сохранить")
        grp.addWidget(QLabel("SMTP:"))
        grp.addWidget(self.ed_host, 1)
        grp.addWidget(self.ed_user)
        grp.addWidget(self.ed_pass)
        grp.addWidget(bsave)
        v.addLayout(grp)

        v.addWidget(QLabel("Почтовый ящик Тех. поддержки: support@fixintel.ru"
                           ""))
        bar = QHBoxLayout()
        bref = QPushButton("Обновить историю")
        self.lbl = QLabel("")
        bar.addWidget(bref)
        bar.addWidget(self.lbl, 1)
        v.addLayout(bar)

        self.listw = QListWidget()
        self.listw.setMaximumHeight(170)
        v.addWidget(self.listw)

        v.addWidget(QLabel("Тема:"))
        self.ed_subj = QLineEdit()
        self.ed_subj.setPlaceholderText("Коротко о проблеме")
        v.addWidget(self.ed_subj)
        v.addWidget(QLabel("Текст обращения:"))
        self.ed_body = QTextEdit()
        self.ed_body.setPlaceholderText("Опишите проблему: что делали, что увидели, тексты ошибок...")
        v.addWidget(self.ed_body, 1)
        bsend = QPushButton(" Отправить обращение разработчику")
        v.addWidget(bsend)

        bsave.clicked.connect(self._save)
        bref.clicked.connect(self._load)
        bsend.clicked.connect(self._send)
        self.listw.currentRowChanged.connect(self._open)
        self._load_settings()
        self._load()

    def _get(self, path):
        r = self.api.session.get(self.api._url(path), timeout=20)
        r.raise_for_status()
        return r.json()

    def _load_settings(self):
        try:
            s = self._get("/support/settings")
            self.ed_host.setText(str(s.get("smtp_host") or ""))
            self.ed_user.setText(str(s.get("smtp_user") or ""))
            self.ed_pass.setText("" if not s.get("smtp_password") else "saved")
        except Exception as e:
            self.lbl.setText("Настройки: %s" % str(e)[:150])

    def _save(self):
        payload = {"smtp_host": self.ed_host.text().strip(),
                   "smtp_port": 465,
                   "smtp_user": self.ed_user.text().strip(),
                   "enabled": True}
        if self.ed_pass.text() and self.ed_pass.text() != "saved":
            payload["smtp_password"] = self.ed_pass.text().strip()
        try:
            r = self.api.session.put(self.api._url("/support/settings"), json=payload, timeout=20)
            self.lbl.setText("Сохранено (%s). Обращения уходят на support@fixintel.ru." % r.status_code)
        except Exception as e:
            self.lbl.setText("Ошибка: %s" % str(e)[:150])

    def _load(self):
        try:
            d = self._get("/support/outbox")
        except Exception as e:
            self.lbl.setText("История: %s" % str(e)[:150])
            return
        rows = d.get("items", []) if isinstance(d, dict) else []
        self._rows = rows
        self.listw.clear()
        for t in rows:
            mark = {"sent": "✔", "error": "✖"}.get(t.get("status"), "?")
            it = QListWidgetItem("%s %s  %s" % (mark, str(t.get("created_at") or "")[:16],
                                                t.get("subject") or "(без темы)"))
            if t.get("status") == "error":
                it.setToolTip(str(t.get("error") or "")[:300])
            it.setData(Qt.ItemDataRole.UserRole, t.get("id"))
            self.listw.addItem(it)

    def _open(self, row):
        if row < 0 or row >= len(getattr(self, "_rows", [])):
            return
        oid = self._rows[row].get("id")
        try:
            d = self._get("/support/outbox/%s" % oid)
        except Exception:
            return
        self.ed_subj.setText(str(d.get("subject") or ""))
        self.ed_body.setPlainText(str(d.get("body") or ""))

    def _send(self):
        text = self.ed_body.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Поддержка", "Напишите текст обращения.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            r = self.api.session.post(self.api._url("/support/send"),
                                      json={"subject": self.ed_subj.text().strip(), "text": text},
                                      timeout=40)
        finally:
            QApplication.restoreOverrideCursor()
        if r.status_code < 300:
            self.ed_body.clear()
            self.lbl.setText("Обращение отправлено на support@fixintel.ru.")
            self._load()
        else:
            try:
                detail = r.json().get("detail", r.text[:250])
            except Exception:
                detail = r.text[:250]
            QMessageBox.warning(self, "Поддержка", "Ошибка %s:\n%s" % (r.status_code, detail))
