"""FitIntel Pro — Setup Tab (статус мастера установки)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme


class SetupWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/setup/status"))
            resp.raise_for_status()
            self.finished.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))


STEP_LABELS = {
    "database": "База данных",
    "license": "Лицензия",
    "admin": "Администратор",
    "club": "Профиль клуба",
    "devices": "Устройства",
    "tariffs": "Тарифы",
    "complete": "Завершение",
}


class SetupTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _card(self, title: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:20px; color:{theme.fg()};'>—</b><br>"
                     f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")
        lbl.setStyleSheet(theme.card_style())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _set_card(self, lbl, title, value, ok=True):
        color = "#059669" if ok else "#ef4444"
        lbl.setText(f"<b style='font-size:20px; color:{color};'>{value}</b><br>"
                    f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.c_lic = self._card("Лицензия")
        self.c_complete = self._card("Установка")
        self.c_step = self._card("Текущий шаг")
        for c in (self.c_lic, self.c_complete, self.c_step):
            row.addWidget(c)
        row.addStretch()
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Шаг мастера", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

        hint = QLabel("Настройка шагов (лицензия, устройства, тарифы) выполняется через API мастера: POST /setup/license/activate, /setup/devices, /setup/complete")
        hint.setStyleSheet("color: #64748b; font-size: 12px; padding: 6px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def refresh(self):
        self.worker = SetupWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, data: dict):
        lic = bool(data.get("is_licensed"))
        comp = bool(data.get("is_complete"))
        self._set_card(self.c_lic, "Лицензия", "Активна" if lic else "НЕТ", lic)
        self._set_card(self.c_complete, "Установка", "Завершена" if comp else "Требуется", comp)
        cur = data.get("current_step") or "—"
        self._set_card(self.c_step, "Текущий шаг", STEP_LABELS.get(cur, cur), True)

        steps = data.get("steps", [])
        self.table.setRowCount(len(steps))
        for i, s in enumerate(steps):
            code = s.get("step", "?")
            done = bool(s.get("done"))
            self.table.setItem(i, 0, QTableWidgetItem(STEP_LABELS.get(code, code)))
            item = QTableWidgetItem("Выполнен" if done else "Ожидает")
            item.setForeground(QColor("#059669" if done else "#f59e0b"))
            self.table.setItem(i, 1, item)

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
