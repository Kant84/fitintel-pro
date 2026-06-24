"""FitIntel Pro — Clients Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QDialog, QFormLayout, QMessageBox,
    QHeaderView, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from api import ApiClient


class LoadClientsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            data = self.api.get_clients()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class ClientsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск клиента...")
        self.search.setStyleSheet("padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px;")
        self.search.textChanged.connect(self._filter)
        toolbar.addWidget(self.search)
        toolbar.addStretch()

        btn_add = QPushButton("➕ Добавить клиента")
        btn_add.setStyleSheet(self._btn_primary())
        btn_add.clicked.connect(self._add_client)
        toolbar.addWidget(btn_add)

        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.setStyleSheet(self._btn_secondary())
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "ФИО", "Телефон", "Email", "Статус", "Действия"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(5, 120)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background: #f8fafc;
                padding: 10px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.lbl_count = QLabel("Загрузка...")
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_count)

    def _btn_primary(self) -> str:
        return """
        QPushButton {
            background: #10b981; color: white; border: none; border-radius: 6px;
            padding: 8px 16px; font-weight: 600; font-size: 13px;
        }
        QPushButton:hover { background: #059669; }
        """

    def _btn_secondary(self) -> str:
        return """
        QPushButton {
            background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
            border-radius: 6px; padding: 8px 16px; font-weight: 600; font-size: 13px;
        }
        QPushButton:hover { background: #e2e8f0; }
        """

    def refresh(self):
        self.worker = LoadClientsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: list):
        self._all_data = data
        self._render(data)

    def _on_error(self, msg: str):
        self.lbl_count.setText(f"❌ Ошибка загрузки: {msg}")

    def _render(self, data: list):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", "")[:8])))
            self.table.setItem(i, 1, QTableWidgetItem(row.get("full_name", "—")))
            self.table.setItem(i, 2, QTableWidgetItem(row.get("phone", "—")))
            self.table.setItem(i, 3, QTableWidgetItem(row.get("email", "—")))
            status = "✅ Активен" if row.get("is_active") else "❌ Неактивен"
            self.table.setItem(i, 4, QTableWidgetItem(status))
            self.table.setItem(i, 5, QTableWidgetItem("Редактировать"))
        self.lbl_count.setText(f"Всего клиентов: {len(data)}")

    def _filter(self, text: str):
        if not text:
            self._render(self._all_data)
            return
        filtered = [r for r in self._all_data if text.lower() in str(r).lower()]
        self._render(filtered)

    def _add_client(self):
        QMessageBox.information(self, "Добавление", "Форма добавления клиента будет здесь.
Используйте API или Swagger для создания.")
