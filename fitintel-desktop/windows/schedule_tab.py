"""FitIntel Pro — Schedule Tab (записи на услуги: просмотр + добавление + отмена)"""
from uuid import UUID

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QDateTimeEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme


class ScheduleWorker(QThread):
    finished = pyqtSignal(list)
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
            self.finished.emit(rows if isinstance(rows, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class NewBookingDialog(QDialog):
    """Диалог добавления записи: клиент + услуга + дата/время"""

    def __init__(self, api: ApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.booking = None
        self.setWindowTitle("Новая запись")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)

        self.client = QComboBox()
        self._clients = []
        try:
            for c in api.get_clients():
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x) or "—"
                self._clients.append((c.get("id"), fio))
                self.client.addItem(fio)
        except Exception:
            pass
        layout.addRow("Клиент:", self.client)

        self.service = QComboBox()
        self._services = []
        try:
            resp = api.session.get(api._url("/services"))
            resp.raise_for_status()
            for s in resp.json():
                if s.get("is_active", True):
                    self._services.append((s.get("id"), s.get("name", "—")))
                    self.service.addItem(s.get("name", "—"))
        except Exception:
            pass
        layout.addRow("Услуга:", self.service)

        self.when = QDateTimeEdit()
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("yyyy-MM-dd HH:mm")
        from PyQt6.QtCore import QDateTime
        self.when.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        layout.addRow("Дата и время:", self.when)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Записать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _submit(self):
        if not self._clients or not self._services:
            QMessageBox.warning(self, "Запись", "Нет данных: проверьте клиентов и услуги")
            return
        client_id = self._clients[self.client.currentIndex()][0]
        service_id = self._services[self.service.currentIndex()][0]
        try:
            resp = self.api.session.post(
                self.api._url(f"/services/{service_id}/book"),
                json={"client_id": str(client_id),
                      "service_id": str(service_id),
                      "booking_date": self.when.dateTime().toString("yyyy-MM-ddTHH:mm:ss")})
            if resp.status_code == 201:
                self.booking = resp.json()
                self.accept()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Запись не создана", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


class ScheduleTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._rows = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        btn_add = QPushButton("＋ Добавить запись")
        btn_add.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_add.clicked.connect(self._add_booking)
        btn_cancel = QPushButton("Отменить запись")
        btn_cancel.setStyleSheet("QPushButton { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_cancel.clicked.connect(self._cancel_booking)
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_refresh.clicked.connect(self.refresh)
        row.addWidget(btn_add)
        row.addWidget(btn_cancel)
        row.addStretch()
        row.addWidget(btn_refresh)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Время", "Клиент", "Услуга", "Тренер", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = ScheduleWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, rows: list):
        self._rows = rows
        self.table.setRowCount(max(len(rows), 1))
        if not rows:
            self.table.setItem(0, 0, QTableWidgetItem("Записей пока нет"))
            self.table.setSpan(0, 0, 1, 6)
            return
        for i, r in enumerate(rows):
            raw_date = str(r.get("booking_date") or "")
            self.table.setItem(i, 0, QTableWidgetItem(raw_date[:10] or "—"))
            self.table.setItem(i, 1, QTableWidgetItem(raw_date[11:16] or "—"))
            self.table.setItem(i, 2, QTableWidgetItem(str(r.get("client_name") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("service_name") or "—")))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("trainer_name") or "—")))
            st = str(r.get("status") or "—")
            item = QTableWidgetItem(st)
            if st.lower() in ("confirmed", "booked", "active", "new"):
                item.setForeground(QColor("#059669"))
            elif st.lower() in ("cancelled", "canceled"):
                item.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 5, item)

    def _on_error(self, msg: str):
        self._rows = []
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
        self.table.setSpan(0, 0, 1, 6)

    def _add_booking(self):
        dlg = NewBookingDialog(self.api, self)
        if dlg.exec() and dlg.booking:
            QMessageBox.information(self, "Запись", "Запись создана")
            self.refresh()

    def _cancel_booking(self):
        idx = self.table.currentRow()
        if idx < 0 or idx >= len(self._rows):
            QMessageBox.information(self, "Отмена записи", "Выберите строку в таблице")
            return
        booking = self._rows[idx]
        bid = booking.get("id")
        name = booking.get("client_name", "—")
        dt = str(booking.get("booking_date") or "")[:16].replace("T", " ")
        if QMessageBox.question(
                self, "Отмена записи",
                f"Отменить запись:\n{name} — {dt}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            resp = self.api.session.post(self.api._url(f"/services/bookings/{bid}/cancel"))
            if resp.status_code in (200, 201, 204):
                QMessageBox.information(self, "Отмена записи", "Запись отменена")
                self.refresh()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Не удалось отменить", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))