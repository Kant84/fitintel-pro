"""FitIntel Pro — Reports Tab (операционные отчёты клуба за период)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate

from api import ApiClient
from windows import theme


class ReportWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient, df: str, dt: str):
        super().__init__()
        self.api = api
        self.df = df
        self.dt = dt

    def run(self):
        try:
            r = self.api.session.get(
                self.api._url("/reports/operational"),
                params={"date_from": self.df, "date_to": self.dt})
            r.raise_for_status()
            self.finished.emit(r.json())
        except Exception as e:
            self.error.emit(str(e))


class ReportsTab(QWidget):
    ROWS = [
        ("revenue", "Выручка (платежи), ₽"),
        ("payments_count", "Количество платежей"),
        ("refunds_sum", "Возвраты, ₽"),
        ("visits_count", "Посещений (входов)"),
        ("new_clients", "Новых клиентов"),
        ("new_subscriptions", "Продано абонементов"),
        ("sales_total", "Продажи магазина, ₽"),
    ]

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
        row.addWidget(QLabel("Период с:"))
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.dt_from)
        row.addWidget(QLabel("по:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.dt_to)
        btn = QPushButton("Сформировать")
        btn.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Показатель", "Значение"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        df = self.dt_from.date().toString("yyyy-MM-dd")
        dt = self.dt_to.date().toString("yyyy-MM-dd")
        self.worker = ReportWorker(self.api, df, dt)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: dict):
        self.table.setRowCount(len(self.ROWS))
        for i, (key, label) in enumerate(self.ROWS):
            val = data.get(key)
            txt = "—" if val is None else (f"{val:,.2f}" if isinstance(val, float) else str(val))
            self.table.setItem(i, 0, QTableWidgetItem(label))
            self.table.setItem(i, 1, QTableWidgetItem(txt))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка формирования: {msg}"))


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = ReportsTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Отчёты")
        except Exception as e:
            print("print btn:", e)
    ReportsTab.__init__ = _e63_init
    print("E63 print OK: reports_tab.py")
except Exception as e:
    print("E63 FAIL:", e)