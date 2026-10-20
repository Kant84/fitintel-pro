# -*- coding: utf-8 -*-
"""W12: Service-аккаунты — токены для интеграций (боты, шлюзы, воркеры)."""
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMessageBox,
    QAbstractItemView, QSpinBox, QCheckBox, QApplication)

SCOPE_PRESETS = [
    ("clients:read", "Чтение клиентов"),
    ("notifications:send", "Отправка уведомлений"),
    ("access:verify", "Проверка доступа (турникет)"),
    ("payments:read", "Чтение платежей"),
    ("payments:export", "Экспорт платежей"),
    ("media:write", "Запись медиа (миграции)"),
    ("bookings:read", "Чтение записей"),
]


class ServiceAccountsTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)

        note = QLabel(
            "Service-аккаунты — API-токены для программ (MAX/Telegram-боты, шлюзы турникетов, ОФД, "
            "выгрузки). Правило: одна интеграция = один аккаунт с узкими scopes. "
            "Токен показывается ОДИН раз при создании — сразу сохраните.")
        note.setWordWrap(True)
        lay.addWidget(note)

        bar = QHBoxLayout()
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Имя (например: telegram-bot, turnstile-gateway)")
        bar.addWidget(self.ed_name, 1)
        self.sp_ttl = QSpinBox()
        self.sp_ttl.setRange(1, 3650)
        self.sp_ttl.setValue(365)
        self.sp_ttl.setSuffix(" дн")
        bar.addWidget(self.sp_ttl)
        b = QPushButton(" Создать")
        b.clicked.connect(self._create)
        bar.addWidget(b)
        b2 = QPushButton("Отозвать выбранный")
        b2.clicked.connect(self._revoke)
        bar.addWidget(b2)
        b3 = QPushButton("Обновить")
        b3.clicked.connect(self.load)
        bar.addWidget(b)
        bar.addWidget(b2)
        bar.addWidget(b3)
        lay.addLayout(bar)

        self.chk_scopes = []
        sc = QHBoxLayout()
        for code, label in SCOPE_PRESETS:
            cb = QCheckBox(label)
            cb.setProperty("scope", code)
            self.chk_scopes.append(cb)
            sc.addWidget(cb)
        sc.addStretch(1)
        lay.addLayout(sc)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(
            ["Имя", "Scopes", "Создан", "Истекает", "Последнее использование", "Отозван"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        lay.addWidget(self.tbl, 1)

        self.load()

    def _get(self, path):
        r = self.api.session.get(self.api._url(path), timeout=20)
        r.raise_for_status()
        return r.json()

    def _post(self, path, data):
        r = self.api.session.post(self.api._url(path), json=data, timeout=20)
        r.raise_for_status()
        return r.json()

    def load(self):
        try:
            d = self._get("/analytics/w12/service-accounts")
            if d.get("error"):
                self.tbl.setRowCount(1)
                self.tbl.setItem(0, 0, QTableWidgetItem("Нет доступа: " + d["error"]))
                return
            rows = d.get("items", [])
        except Exception as e:
            self.tbl.setRowCount(1)
            self.tbl.setItem(0, 0, QTableWidgetItem("Ошибка: %s" % str(e)[:150]))
            return
        self.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(r.get("name") or "")))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(r.get("scopes") or "")))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(r.get("created_at") or "")[:19]))
            self.tbl.setItem(i, 3, QTableWidgetItem(str(r.get("expires_at") or "")[:19]))
            self.tbl.setItem(i, 4, QTableWidgetItem(str(r.get("last_used_at") or "—")[:19]))
            rv = r.get("revoked_at")
            it = QTableWidgetItem("ДА" if rv else "—")
            if rv:
                it.setForeground(Qt.GlobalColor.red)
            self.tbl.setItem(i, 5, it)
            self.tbl.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.get("id"))

    def _create(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Service-аккаунт", "Укажите имя")
            return
        scopes = [cb.property("scope") for cb in self.chk_scopes if cb.isChecked()]
        try:
            d = self._post("/analytics/w12/service-accounts",
                           {"name": name, "scopes": scopes, "ttl_days": self.sp_ttl.value()})
        except Exception as e:
            QMessageBox.warning(self, "Service-аккаунт", str(e)[:200])
            return
        if not d.get("ok"):
            QMessageBox.warning(self, "Service-аккаунт", str(d.get("error", "ошибка")))
            return
        tok = d.get("token", "")
        QApplication.clipboard().setText(tok)
        QMessageBox.information(
            self, "Токен создан (скопирован в буфер)",
            "Сохраните токен — он больше не будет показан:\n\n%s\n\nИмя: %s\nScopes: %s"
            % (tok, name, ", ".join(scopes) or "—"))
        self.ed_name.clear()
        for cb in self.chk_scopes:
            cb.setChecked(False)
        self.load()

    def _revoke(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        it = self.tbl.item(row, 0)
        sid = it.data(Qt.ItemDataRole.UserRole) if it else None
        if not sid:
            return
        if QMessageBox.question(self, "Отзыв", "Отозвать токен? Интеграция перестанет работать.") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._post("/analytics/w12/service-accounts/%s/revoke" % sid, {})
            self.load()
        except Exception as e:
            QMessageBox.warning(self, "Отзыв", str(e)[:200])