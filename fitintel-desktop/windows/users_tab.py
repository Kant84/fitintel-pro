"""FitIntel Pro — Users Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient


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
        self.table.setStyleSheet("""
            QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; border: none; border-bottom: 1px solid #e2e8f0; }
        """)
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

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
