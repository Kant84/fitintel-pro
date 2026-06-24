"""FitIntel Pro — Subscriptions Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api import ApiClient


class LoadSubsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            data = self.api.get_subscriptions()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class SubscriptionsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск абонемента...")
        self.search.setStyleSheet("padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px;")
        toolbar.addWidget(self.search)
        toolbar.addStretch()

        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.setStyleSheet(self._btn_secondary())
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Клиент", "Тариф", "Начало", "Конец", "Статус", "Действия"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; border: none; border-bottom: 1px solid #e2e8f0; }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.lbl_count = QLabel("Загрузка...")
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_count)

    def _btn_secondary(self) -> str:
        return "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; } QPushButton:hover { background: #e2e8f0; }"

    def refresh(self):
        self.worker = LoadSubsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: list):
        self._all_data = data
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", "")[:8])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_id", "—"))))
            self.table.setItem(i, 2, QTableWidgetItem(row.get("tariff_name", "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("start_date", "—"))[:10]))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("end_date", "—"))[:10]))
            status = row.get("status", "—")
            color = "#10b981" if status == "active" else "#ef4444" if status == "expired" else "#f59e0b"
            item = QTableWidgetItem(status.upper())
            item.setForeground(Qt.GlobalColor.darkGreen if status == "active" else Qt.GlobalColor.red)
            self.table.setItem(i, 5, item)
            self.table.setItem(i, 6, QTableWidgetItem("Заморозить / Продлить"))
        self.lbl_count.setText(f"Всего абонементов: {len(data)}")

    def _on_error(self, msg: str):
        self.lbl_count.setText(f"❌ Ошибка: {msg}")
