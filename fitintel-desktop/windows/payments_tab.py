"""FitIntel Pro — Payments Tab (проводки + отчёт продаж)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from api import ApiClient


class PaymentsWorker(QThread):
    finished = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            entries = self.api.get_accounting_entries()
            try:
                report = self.api.get_sales_report()
            except Exception:
                report = {}
            self.finished.emit(entries, report)
        except Exception as e:
            self.error.emit(str(e))


class PaymentsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _card(self, title: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:22px; color:#0f172a;'>—</b><br>"
                     f"<span style='font-size:12px; color:#64748b;'>{title}</span>")
        lbl.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; min-width: 160px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _set_card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:22px; color:#0f172a;'>{value}</b><br>"
                    f"<span style='font-size:12px; color:#64748b;'>{title}</span>")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.c_total = self._card("Проводок всего")
        self.c_sum = self._card("Сумма, ₽")
        self.c_today = self._card("Источники")
        for c in (self.c_total, self.c_sum, self.c_today):
            row.addWidget(c)
        row.addStretch()
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Дебет", "Кредит", "Сумма, ₽", "Источник", "Описание"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; border: none; border-bottom: 1px solid #e2e8f0; }
        """)
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = PaymentsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, entries: list, report: dict):
        total_sum = sum(float(e.get("amount") or 0) for e in entries)
        sources = sorted({str(e.get("source") or "—") for e in entries})
        self._set_card(self.c_total, "Проводок всего", len(entries))
        self._set_card(self.c_sum, "Сумма, ₽", f"{total_sum:,.0f}".replace(",", " "))
        self._set_card(self.c_today, "Источники", len(sources))

        self.table.setRowCount(len(entries))
        for i, e in enumerate(entries):
            self.table.setItem(i, 0, QTableWidgetItem(str(e.get("entry_date") or "—")[:10]))
            self.table.setItem(i, 1, QTableWidgetItem(str(e.get("debit_account") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(e.get("credit_account") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(e.get("amount") or "—")))
            self.table.setItem(i, 4, QTableWidgetItem(str(e.get("source") or "—")))
            self.table.setItem(i, 5, QTableWidgetItem(str(e.get("description") or "")[:80]))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
