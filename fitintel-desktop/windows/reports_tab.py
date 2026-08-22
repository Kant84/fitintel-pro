"""FitIntel Pro — Reports Tab (календарь отчётности ФНС)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme


class ReportsWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/reporting/calendar"))
            resp.raise_for_status()
            self.finished.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))


class ReportsTab(QWidget):
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
        self.lbl_year = QLabel("Отчётный календарь")
        self.lbl_year.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        row.addWidget(self.lbl_year)
        row.addStretch()
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Отчёт", "Период", "Срок сдачи"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

        hint = QLabel("Выгрузки 6-НДФЛ / РСВ / УСН доступны через API: /reporting/6ndfl/export, /reporting/rsv/export, /reporting/usn-declaration")
        hint.setStyleSheet("color: #64748b; font-size: 12px; padding: 6px;")
        layout.addWidget(hint)

    def refresh(self):
        self.worker = ReportsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: dict):
        year = data.get("year", "")
        self.lbl_year.setText(f"Отчётный календарь {year}")
        deadlines = data.get("deadlines", [])
        self.table.setRowCount(len(deadlines))
        for i, d in enumerate(deadlines):
            self.table.setItem(i, 0, QTableWidgetItem(str(d.get("report") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(d.get("period") or "—")))
            dl = QTableWidgetItem(str(d.get("deadline") or "—"))
            dl.setForeground(QColor("#b45309"))
            self.table.setItem(i, 2, dl)

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
