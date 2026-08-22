"""FitIntel Pro — Users Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class UsersWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            self.finished.emit(self.api.get_users())
        except Exception as e:
            self.error.emit(str(e))


class UsersTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.addStretch()
        b_add = QPushButton("Создать пользователя")
        b_add.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_add.clicked.connect(self._add)
        row.addWidget(b_add)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Логин", "Email", "Роли", "Прав", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = UsersWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, users: list):
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(u.get("username") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(u.get("email") or "—")))
            roles = u.get("roles") or []
            if isinstance(roles, list):
                rtxt = ", ".join(str(r.get("name", r)) if isinstance(r, dict) else str(r) for r in roles)
            else:
                rtxt = str(roles)
            self.table.setItem(i, 2, QTableWidgetItem(rtxt or "—"))
            perms = u.get("permissions") or []
            self.table.setItem(i, 3, QTableWidgetItem(str(len(perms)) if isinstance(perms, list) else "—"))
            active = u.get("is_active")
            item = QTableWidgetItem("Активен" if active else "Отключён")
            item.setForeground(QColor("#059669" if active else "#ef4444"))
            self.table.setItem(i, 4, item)

    def _add(self):
        dlg = FormDialog("Новый пользователь", [
            ("username", "Логин *"),
            ("email", "Email *"),
            ("password", "Пароль *"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["username"] or not v["password"]:
            QMessageBox.warning(self, "Ошибка", "Логин и пароль обязательны")
            return
        try:
            r = self.api.session.post(self.api._url("/users/"), json=v)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
