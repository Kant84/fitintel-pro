"""FitIntel Pro — вкладка «Параметры клуба» (W5): временные параметры + лейблы бота.

Данные: GET/PUT /api/v1/club-params, GET/PUT /api/v1/bot-labels.
Клуб правит здесь длительность слота, окна входа, дедлайны, тексты кнопок бота.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal

from api import ApiClient
from windows import theme


class ParamsWorker(QThread):
    finished = pyqtSignal(list)
    labels = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            r = self.api.session.get(self.api._url("/club-params"))
            r.raise_for_status()
            self.finished.emit(r.json())
            r2 = self.api.session.get(self.api._url("/bot-labels"))
            if r2.status_code == 200:
                self.labels.emit(r2.json().get("labels", {}))
        except Exception as e:
            self.error.emit(str(e))


class ClubParamsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._params = []
        self._labels = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel("Все временные правила и тексты бота. Меняется сразу, без перезапуска сервера. "
                      "Двойной клик по строке — изменить значение.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tabs = QTabWidget()
        self.tbl_params = QTableWidget()
        self.tbl_params.setColumnCount(3)
        self.tbl_params.setHorizontalHeaderLabels(["Параметр", "Значение", "Описание"])
        self.tbl_params.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_params.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_params.setStyleSheet(theme.table_style())
        self.tbl_params.itemDoubleClicked.connect(self._edit_param)
        self.tabs.addTab(self.tbl_params, " Временные параметры")

        self.tbl_labels = QTableWidget()
        self.tbl_labels.setColumnCount(2)
        self.tbl_labels.setHorizontalHeaderLabels(["Лейбл", "Текст"])
        self.tbl_labels.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_labels.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_labels.setStyleSheet(theme.table_style())
        self.tbl_labels.itemDoubleClicked.connect(self._edit_label)
        self.tabs.addTab(self.tbl_labels, " Лейблы бота")
        layout.addWidget(self.tabs, 1)

        row = QHBoxLayout()
        rb = QPushButton("Обновить")
        rb.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        rb.clicked.connect(self.refresh)
        row.addWidget(rb)
        row.addStretch()
        layout.addLayout(row)

    def refresh(self):
        self.worker = ParamsWorker(self.api)
        self.worker.finished.connect(self._on_params)
        self.worker.labels.connect(self._on_labels)
        self.worker.error.connect(lambda m: QMessageBox.warning(self, "Параметры", m))
        self.worker.start()

    def _on_params(self, rows: list):
        self._params = rows
        self.tbl_params.setRowCount(len(rows))
        for i, r in enumerate(rows):
            k = QTableWidgetItem(str(r.get("key")))
            k.setData(0x0100, str(r.get("key")))   # UserRole
            self.tbl_params.setItem(i, 0, k)
            self.tbl_params.setItem(i, 1, QTableWidgetItem(str(r.get("value"))))
            self.tbl_params.setItem(i, 2, QTableWidgetItem(str(r.get("description") or "")))

    def _on_labels(self, labels: dict):
        self._labels = labels
        keys = sorted(labels.keys())
        self.tbl_labels.setRowCount(len(keys))
        for i, k in enumerate(keys):
            it = QTableWidgetItem(k)
            it.setData(0x0100, k)
            self.tbl_labels.setItem(i, 0, it)
            self.tbl_labels.setItem(i, 1, QTableWidgetItem(str(labels[k])))

    def _edit_param(self, item):
        row = item.row()
        key = self.tbl_params.item(row, 0).data(0x0100)
        cur = self.tbl_params.item(row, 1).text()
        val, ok = QInputDialog.getText(self, f"Параметр {key}", "Новое значение:", text=cur)
        if not ok or val == cur:
            return
        try:
            r = self.api.session.put(self.api._url(f"/club-params/{key}"), json={"value": val})
            if r.status_code == 200:
                QMessageBox.information(self, "Сохранено", f"{key} = {val}")
                self.refresh()
            else:
                QMessageBox.warning(self, "Не сохранено", r.text()[:200])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _edit_label(self, item):
        row = item.row()
        key = self.tbl_labels.item(row, 0).data(0x0100)
        cur = self.tbl_labels.item(row, 1).text()
        val, ok = QInputDialog.getMultiLineText(self, f"Лейбл {key}", "Текст:", text=cur)
        if not ok or val == cur:
            return
        try:
            r = self.api.session.put(self.api._url(f"/bot-labels/{key}"), json={"value": val})
            if r.status_code == 200:
                self.refresh()
            else:
                QMessageBox.warning(self, "Не сохранено", r.text()[:200])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))