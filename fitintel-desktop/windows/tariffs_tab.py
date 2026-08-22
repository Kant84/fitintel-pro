"""FitIntel Pro — Tariffs Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class TariffsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            resp = self.api.session.get(self.api._url("/tariffs/"))
            resp.raise_for_status()
            body = resp.json()
            if isinstance(body, dict):
                body = body.get("items", [])
            self.finished.emit(body if isinstance(body, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class TariffsTab(QWidget):
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
        row.addStretch()
        btn_add = QPushButton("Создать тариф")
        btn_add.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_add.clicked.connect(self._add)
        row.addWidget(btn_add)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Код", "Название", "Цена", "Дней", "Визитов", "Тип", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = TariffsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, tariffs: list):
        self.table.setRowCount(len(tariffs))
        for i, t in enumerate(tariffs):
            self.table.setItem(i, 0, QTableWidgetItem(str(t.get("code") or "—")))
            self.table.setItem(i, 1, QTableWidgetItem(str(t.get("name") or "—")))
            price = t.get("price")
            cur = t.get("currency") or "RUB"
            self.table.setItem(i, 2, QTableWidgetItem(f"{price} {cur}" if price is not None else "—"))
            self.table.setItem(i, 3, QTableWidgetItem(str(t.get("duration_days") or "—")))
            vl = t.get("visit_limit")
            self.table.setItem(i, 4, QTableWidgetItem(str(vl) if vl else "—"))
            self.table.setItem(i, 5, QTableWidgetItem("Безлимит" if t.get("is_unlimited") else "Лимит"))
            active = t.get("is_active")
            item = QTableWidgetItem("Активен" if active else "Отключён")
            item.setForeground(QColor("#059669" if active else "#ef4444"))
            self.table.setItem(i, 6, item)

    def _add(self):
        dlg = FormDialog("Новый тариф", [
            ("code", "Код (A-Z, 0-9, _) *"),
            ("name", "Название *"),
            ("price", "Цена *", "text", "1000"),
            ("duration_days", "Дней действия *", "text", "30"),
            ("visit_limit", "Лимит визитов (пусто = без лимита)"),
            ("is_unlimited", "Тип", "combo", [("Лимитированный", False), ("Безлимитный", True)]),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["code"] or not v["name"]:
            QMessageBox.warning(self, "Ошибка", "Код и название обязательны")
            return
        payload = {"code": v["code"].upper(), "name": v["name"],
                   "price": float(v["price"] or 0),
                   "duration_days": int(v["duration_days"] or 30),
                   "is_unlimited": bool(v["is_unlimited"])}
        if v["visit_limit"]:
            payload["visit_limit"] = int(v["visit_limit"])
        try:
            r = self.api.session.post(self.api._url("/tariffs/"), json=payload)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка создания", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = TariffsTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Тарифы")
        except Exception as e:
            print("print btn:", e)
    TariffsTab.__init__ = _e63_init
    print("E63 print OK: tariffs_tab.py")
except Exception as e:
    print("E63 FAIL:", e)
