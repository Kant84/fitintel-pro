"""FitIntel Pro — Face ID Tab"""
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QTextEdit, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from api import ApiClient


class VerifyFaceWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient, face_encoding: list, terminal_id: str):
        super().__init__()
        self.api = api
        self.face_encoding = face_encoding
        self.terminal_id = terminal_id

    def run(self):
        try:
            result = self.api.verify_face(self.face_encoding, self.terminal_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LoadLogsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            data = self.api.get_face_logs()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class FaceIDTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh_logs()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("🎭 Face ID — Распознавание лиц")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)

        # Terminal selector
        term_layout = QHBoxLayout()
        term_layout.addWidget(QLabel("Терминал:"))
        self.combo_terminal = QComboBox()
        self.combo_terminal.addItems(["desktop-001", "reception-01", "gate-01", "gate-02"])
        self.combo_terminal.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 6px;")
        term_layout.addWidget(self.combo_terminal)
        term_layout.addStretch()
        layout.addLayout(term_layout)

        # Simulation buttons (until real camera connected)
        btn_layout = QHBoxLayout()

        btn_sim_grant = QPushButton("✅ Симуляция: Разрешить доступ")
        btn_sim_grant.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 12px 24px; font-weight: 600; } QPushButton:hover { background: #059669; }")
        btn_sim_grant.clicked.connect(lambda: self._simulate_verify(True))
        btn_layout.addWidget(btn_sim_grant)

        btn_sim_deny = QPushButton("❌ Симуляция: Запретить доступ")
        btn_sim_deny.setStyleSheet("QPushButton { background: #ef4444; color: white; border: none; border-radius: 6px; padding: 12px 24px; font-weight: 600; } QPushButton:hover { background: #dc2626; }")
        btn_sim_deny.clicked.connect(lambda: self._simulate_verify(False))
        btn_layout.addWidget(btn_sim_deny)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Result display
        self.lbl_result = QLabel("Нажмите кнопку для симуляции распознавания")
        self.lbl_result.setStyleSheet("padding: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px; color: #475569;")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setMinimumHeight(80)
        layout.addWidget(self.lbl_result)

        # Logs
        logs_header = QHBoxLayout()
        logs_header.addWidget(QLabel("📋 Журнал распознавания"))
        logs_header.addStretch()
        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.setStyleSheet(self._btn_secondary())
        btn_refresh.clicked.connect(self.refresh_logs)
        logs_header.addWidget(btn_refresh)
        layout.addLayout(logs_header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Время", "Терминал", "Пользователь", "Тип", "Результат", "Причина"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; }
            QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; border: none; border-bottom: 1px solid #e2e8f0; }
        """)
        layout.addWidget(self.table)

    def _btn_secondary(self) -> str:
        return "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; } QPushButton:hover { background: #e2e8f0; }"

    def _simulate_verify(self, granted: bool):
        """Симуляция вектора лица (128 значений) для тестирования API"""
        face_encoding = [random.random() for _ in range(128)]
        terminal_id = self.combo_terminal.currentText()

        self.lbl_result.setText(f"⏳ Отправка запроса на терминал {terminal_id}...")

        self.worker = VerifyFaceWorker(self.api, face_encoding, terminal_id)
        self.worker.finished.connect(lambda r: self._on_verify_result(r, granted))
        self.worker.error.connect(self._on_verify_error)
        self.worker.start()

    def _on_verify_result(self, result: dict, simulated_granted: bool):
        access = result.get("access_granted", False)
        reason = result.get("reason", "—")
        user = result.get("user_name", "Неизвестный")
        user_type = result.get("user_type", "—")

        if access:
            self.lbl_result.setStyleSheet("padding: 20px; background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; font-size: 16px; color: #065f46; font-weight: 600;")
            self.lbl_result.setText(f"✅ ДОСТУП РАЗРЕШЁН

Пользователь: {user}
Тип: {user_type}
Причина: {reason}")
        else:
            self.lbl_result.setStyleSheet("padding: 20px; background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; font-size: 16px; color: #991b1b; font-weight: 600;")
            self.lbl_result.setText(f"❌ ДОСТУП ЗАПРЕЩЁН

Причина: {reason}")

        self.refresh_logs()

    def _on_verify_error(self, msg: str):
        self.lbl_result.setStyleSheet("padding: 20px; background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; font-size: 14px; color: #991b1b;")
        self.lbl_result.setText(f"❌ Ошибка API: {msg}")

    def refresh_logs(self):
        self.worker_logs = LoadLogsWorker(self.api)
        self.worker_logs.finished.connect(self._on_logs_loaded)
        self.worker_logs.error.connect(lambda _: None)
        self.worker_logs.start()

    def _on_logs_loaded(self, data: list):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("created_at", "—"))[:16]))
            self.table.setItem(i, 1, QTableWidgetItem(row.get("terminal_id", "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("user_id", "—"))))
            self.table.setItem(i, 3, QTableWidgetItem(row.get("user_type", "—")))
            status = "✅ Разрешён" if row.get("status") == "granted" else "❌ Запрещён"
            self.table.setItem(i, 4, QTableWidgetItem(status))
            self.table.setItem(i, 5, QTableWidgetItem(row.get("reason", "—")))
