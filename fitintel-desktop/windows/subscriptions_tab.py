"""FitIntel Pro — Subscriptions Tab (продажа, заморозка)"""
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class SubsWorker(QThread):
    finished = pyqtSignal(list, list, list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            subs = self.api.get_subscriptions()
            clients = self.api.get_clients()
            resp = self.api.session.get(self.api._url("/tariffs/"))
            tariffs = resp.json().get("items", []) if resp.status_code == 200 else []
            self.finished.emit(subs, clients, tariffs)
        except Exception as e:
            self.error.emit(str(e))


def fio(c: dict) -> str:
    return " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x) or "—"


class SubscriptionsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._subs = []
        self._clients = []
        self._tariffs = []
        self._cmap = {}
        self._tmap = {}
        self._build_ui()
        self.refresh()

    def _btn(self, text, color="#f1f5f9", fg="#475569"):
        b = QPushButton(text)
        b.setStyleSheet(f"QPushButton {{ background: {color}; color: {fg}; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }}")
        return b

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.addStretch()
        b_sell = self._btn("＋ Продать абонемент", "#10b981", "white")
        b_sell.clicked.connect(self._sell)
        row.addWidget(b_sell)
        b_fr = self._btn("❄ Заморозить")
        b_fr.clicked.connect(self._freeze)
        row.addWidget(b_fr)
        b_uf = self._btn("▶ Разморозить")
        b_uf.clicked.connect(self._unfreeze)
        row.addWidget(b_uf)
        b_ref = self._btn("Обновить")
        b_ref.clicked.connect(self.refresh)
        row.addWidget(b_ref)
        layout.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Клиент", "Тариф", "Начало", "Конец", "Статус", "Осталось визитов"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = SubsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, subs: list, clients: list, tariffs: list):
        self._subs = subs
        self._clients = clients
        self._tariffs = tariffs
        self._cmap = {str(c.get("id")): fio(c) for c in clients}
        self._tmap = {str(t.get("id")): t.get("name", "—") for t in tariffs}
        self.table.setRowCount(len(subs))
        for i, s in enumerate(subs):
            item0 = QTableWidgetItem(self._cmap.get(str(s.get("client_id")), "—"))
            item0.setData(Qt.ItemDataRole.UserRole, str(s.get("id")))
            self.table.setItem(i, 0, item0)
            self.table.setItem(i, 1, QTableWidgetItem(self._tmap.get(str(s.get("tariff_id")), str(s.get("tariff_id") or "—")[:8])))
            self.table.setItem(i, 2, QTableWidgetItem(str(s.get("start_date") or "")[:10]))
            self.table.setItem(i, 3, QTableWidgetItem(str(s.get("end_date") or "")[:10]))
            st = str(s.get("status") or "—")
            item = QTableWidgetItem(st)
            color = {"ACTIVE": "#059669", "FROZEN": "#3b82f6", "EXPIRED": "#ef4444", "CANCELLED": "#94a3b8"}.get(st.upper(), "#0f172a")
            item.setForeground(QColor(color))
            self.table.setItem(i, 4, item)
            vl = s.get("visits_left", s.get("remaining_visits"))
            self.table.setItem(i, 5, QTableWidgetItem(str(vl) if vl is not None else "—"))

    def _selected_sub(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Сначала выберите абонемент")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _sell(self):
        if not self._clients or not self._tariffs:
            QMessageBox.warning(self, "Нет данных", "Нужны клиенты и тарифы")
            return
        fields = [
            ("client_id", "Клиент *", "combo",
             [(f"{fio(c)} ({c.get('phone', '')})", str(c.get("id"))) for c in self._clients[:200]]),
            ("tariff_id", "Тариф *", "combo",
             [(f"{t.get('name')} — {t.get('price')} {t.get('currency', 'RUB')}", str(t.get("id"))) for t in self._tariffs if t.get("is_active")]),
            ("start_date", "Дата начала (ГГГГ-ММ-ДД) *", "text", str(date.today())),
        ]
        dlg = FormDialog("Продажа абонемента", fields, self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            self.api.create_subscription(v)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка продажи", str(e))

    def _freeze(self):
        sid = self._selected_sub()
        if not sid:
            return
        dlg = FormDialog("Заморозка", [
            ("frozen_until", "Заморозить до (ГГГГ-ММ-ДД, пусто = без срока)"),
            ("reason", "Причина"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = {k: val for k, val in dlg.values().items() if val}
        try:
            self.api.freeze_subscription(sid) if not v else self.api.session.post(
                self.api._url(f"/subscriptions/{sid}/freeze"), json=v).raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _unfreeze(self):
        sid = self._selected_sub()
        if not sid:
            return
        try:
            self.api.unfreeze_subscription(sid)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
