"""FitIntel Pro — Visits Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api import ApiClient


class LoadVisitsWorker(QThread):
    finished = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            visits = self.api.get_visits()
            stats = self.api.get_visit_stats()
            self.finished.emit(visits, stats)
        except Exception as e:
            self.error.emit(str(e))


class VisitsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Stats cards
        stats = QHBoxLayout()
        self.lbl_today = self._stat_card("Сегодня", "0")
        self.lbl_week = self._stat_card("Неделя", "0")
        self.lbl_month = self._stat_card("Месяц", "0")
        stats.addWidget(self.lbl_today)
        stats.addWidget(self.lbl_week)
        stats.addWidget(self.lbl_month)
        layout.addLayout(stats)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.setStyleSheet(self._btn_secondary())
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Клиент", "Тип", "Время", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; border: none; border-bottom: 1px solid #e2e8f0; }
        """)
        layout.addWidget(self.table)

    def _stat_card(self, title: str, value: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:24px; color:#0f172a;'>{value}</b><br><span style='font-size:12px; color:#64748b;'>{title}</span>")
        lbl.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; min-width: 120px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _btn_secondary(self) -> str:
        return "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; } QPushButton:hover { background: #e2e8f0; }"

    def refresh(self):
        self.worker = LoadVisitsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, visits: list, stats: dict):
        self.lbl_today.setText(f"<b style='font-size:24px; color:#0f172a;'>{stats.get('today', 0)}</b><br><span style='font-size:12px; color:#64748b;'>Сегодня</span>")
        self.lbl_week.setText(f"<b style='font-size:24px; color:#0f172a;'>{stats.get('week', 0)}</b><br><span style='font-size:12px; color:#64748b;'>Неделя</span>")
        self.lbl_month.setText(f"<b style='font-size:24px; color:#0f172a;'>{stats.get('month', 0)}</b><br><span style='font-size:12px; color:#64748b;'>Месяц</span>")

        self.table.setRowCount(len(visits))
        for i, row in enumerate(visits):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", "")[:8])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", "—"))))
            self.table.setItem(i, 2, QTableWidgetItem(row.get("visit_type", "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("created_at", "—"))[:16]))
            self.table.setItem(i, 4, QTableWidgetItem(row.get("status", "—")))

    def _on_error(self, msg: str):
        pass
