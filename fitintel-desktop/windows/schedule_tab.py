"""FitIntel Pro — Schedule Tab (записи на услуги)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme


class ScheduleWorker(QThread):
    finished = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/services/trainer-schedule"))
            resp.raise_for_status()
            rows = resp.json()
            if isinstance(rows, dict):
                rows = rows.get("items", rows.get("schedule", []))
            clients = self.api.get_clients()
            cmap = {}
            for c in clients:
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x)
                cmap[str(c.get("id"))] = fio or "—"
            self.finished.emit(rows if isinstance(rows, list) else [], cmap)
        except Exception as e:
            self.error.emit(str(e))


class ScheduleTab(QWidget):
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
            ["Дата", "Клиент", "Услуга", "Статус", "Создано"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = ScheduleWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, rows: list, cmap: dict):
        self.table.setRowCount(max(len(rows), 1))
        if not rows:
            self.table.setItem(0, 0, QTableWidgetItem("Записей пока нет"))
            return
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r.get("booking_date") or "—")[:10]))
            self.table.setItem(i, 1, QTableWidgetItem(cmap.get(str(r.get("client_id")), "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(r.get("service_id") or "—")[:12]))
            st = str(r.get("status") or "—")
            item = QTableWidgetItem(st)
            if st.lower() in ("confirmed", "active", "new"):
                item.setForeground(QColor("#059669"))
            elif st.lower() in ("cancelled", "canceled"):
                item.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 3, item)
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("created_at") or "")[:10]))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
