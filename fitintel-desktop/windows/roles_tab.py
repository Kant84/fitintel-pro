"""FitIntel Pro — Roles Tab (RBAC матрица прав)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from api import ApiClient
from windows import theme


class RolesWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/rbac/roles-matrix"))
            resp.raise_for_status()
            body = resp.json()
            if isinstance(body, dict):
                body = body.get("roles", body.get("items", []))
            self.finished.emit(body if isinstance(body, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class RolesTab(QWidget):
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Роль", "Код", "Кол-во прав", "Права (первые)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = RolesWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, roles: list):
        self.table.setRowCount(len(roles))
        for i, r in enumerate(roles):
            perms = r.get("permissions") or []
            if isinstance(perms, list):
                names = [str(p.get("code", p.get("name", p))) if isinstance(p, dict) else str(p) for p in perms]
            else:
                names = [str(perms)]
            self.table.setItem(i, 0, QTableWidgetItem(str(r.get("role_name") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(r.get("role_code") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(len(names))))
            preview = ", ".join(names[:6]) + ("..." if len(names) > 6 else "")
            item = QTableWidgetItem(preview)
            item.setToolTip("\n".join(names))
            self.table.setItem(i, 3, item)

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
