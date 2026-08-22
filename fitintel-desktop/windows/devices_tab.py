"""FitIntel Pro — Devices Tab (DAL)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class DevicesWorker(QThread):
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            devices = self.api.get_devices()
            try:
                drivers = self.api.get_drivers()
            except Exception:
                drivers = []
            self.finished.emit(devices, drivers)
        except Exception as e:
            self.error.emit(str(e))


class DevicesTab(QWidget):
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
        self.lbl_info = QLabel("Устройства подключаются через DAL (E47) и мастер установки (E30)")
        self.lbl_info.setStyleSheet("color: #64748b; font-size: 12px;")
        row.addWidget(self.lbl_info)
        row.addStretch()
        b_disc = QPushButton("Найти устройства")
        b_disc.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_disc.clicked.connect(self._discover)
        row.addWidget(b_disc)
        b_add = QPushButton("Добавить вручную")
        b_add.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_add.clicked.connect(self._add)
        row.addWidget(b_add)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        box_d = QGroupBox("Подключённые устройства")
        dl = QVBoxLayout(box_d)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Тип", "Подключение", "Драйвер", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        dl.addWidget(self.table)
        layout.addWidget(box_d)

        box_dr = QGroupBox("Установленные драйверы")
        drl = QVBoxLayout(box_dr)
        self.tbl_drivers = QTableWidget()
        self.tbl_drivers.setColumnCount(4)
        self.tbl_drivers.setHorizontalHeaderLabels(
            ["Пакет", "Версия", "Статус", "Установлен"])
        self.tbl_drivers.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_drivers.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_drivers.setAlternatingRowColors(True)
        drl.addWidget(self.tbl_drivers)
        layout.addWidget(box_dr)

    def refresh(self):
        self.worker = DevicesWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, devices: list, drivers: list):
        self._drivers = drivers
        self.table.setRowCount(max(len(devices), 1))
        if not devices:
            self.table.setItem(0, 0, QTableWidgetItem(
                "Устройств пока нет — добавьте через мастер установки или POST /dal/drivers/{pkg}/discover"))
        for i, d in enumerate(devices):
            self.table.setItem(i, 0, QTableWidgetItem(str(d.get("name") or d.get("device_name") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(d.get("device_type") or d.get("type") or "—")))
            self.table.setItem(i, 2, QTableWidgetItem(str(d.get("connection_string") or "—")))
            self.table.setItem(i, 3, QTableWidgetItem(str(d.get("driver_package") or d.get("driver") or "—")))
            st = str(d.get("status") or "—")
            item = QTableWidgetItem(st)
            if st.lower() in ("online", "active", "enabled"):
                item.setForeground(QColor("#059669"))
            self.table.setItem(i, 4, item)

        self.tbl_drivers.setRowCount(len(drivers))
        for i, d in enumerate(drivers):
            self.tbl_drivers.setItem(i, 0, QTableWidgetItem(str(d.get("package") or d.get("name") or "—")))
            self.tbl_drivers.setItem(i, 1, QTableWidgetItem(str(d.get("version") or "—")))
            enabled = d.get("is_enabled", d.get("enabled"))
            item = QTableWidgetItem("Включён" if enabled else "Выключен")
            item.setForeground(QColor("#059669" if enabled else "#ef4444"))
            self.tbl_drivers.setItem(i, 2, item)
            self.tbl_drivers.setItem(i, 3, QTableWidgetItem(str(d.get("installed_at") or "")[:10]))

    def _driver_options(self):
        return [(str(d.get("package") or d.get("name")), str(d.get("id") or d.get("driver_id") or d.get("package")))
                for d in getattr(self, "_drivers", [])]

    def _discover(self):
        opts = self._driver_options()
        if not opts:
            QMessageBox.warning(self, "Нет драйверов", "Сначала установите драйвер (DAL)")
            return
        dlg = FormDialog("Поиск устройств", [("driver_id", "Драйвер *", "combo", opts)], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        try:
            r = self.api.session.post(self.api._url("/dal/devices/discover"),
                                      json={"driver_id": dlg.values()["driver_id"]})
            r.raise_for_status()
            res = r.json()
            QMessageBox.information(self, "Поиск завершён", str(res)[:300])
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка поиска", str(e))

    def _add(self):
        opts = self._driver_options()
        if not opts:
            QMessageBox.warning(self, "Нет драйверов", "Сначала установите драйвер (DAL)")
            return
        dlg = FormDialog("Новое устройство", [
            ("driver_id", "Драйвер *", "combo", opts),
            ("name", "Название *"),
            ("connection_string", "Подключение (IP/COM/URL) *"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["name"] or not v["connection_string"]:
            QMessageBox.warning(self, "Ошибка", "Заполните название и подключение")
            return
        try:
            r = self.api.session.post(self.api._url("/dal/devices"), json=v)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
