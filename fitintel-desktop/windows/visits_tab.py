"""FitIntel Pro — Visits Tab (с ФИО и телефоном клиента)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

from api import ApiClient
from windows import theme
from windows.form_dialog import FormDialog


class LoadVisitsWorker(QThread):
    finished = pyqtSignal(list, dict, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            visits = self.api.get_visits()
            stats = self.api.get_visit_stats()
            clients = self.api.get_clients()
            cmap = {}
            for c in clients:
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name"),
                                           c.get("middle_name")) if x)
                cmap[str(c.get("id"))] = (fio or "—", c.get("phone") or "")
            self.finished.emit(visits, stats, cmap)
        except Exception as e:
            self.error.emit(str(e))


class VisitsTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._all_data = []
        self._cmap = {}
        self._build_ui()
        QThread.msleep(0)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        cards = QHBoxLayout()
        self.lbl_today = self._stat_card("Сегодня", "0")
        self.lbl_week = self._stat_card("Неделя", "0")
        self.lbl_month = self._stat_card("Месяц", "0")
        cards.addWidget(self.lbl_today)
        cards.addWidget(self.lbl_week)
        cards.addWidget(self.lbl_month)
        cards.addStretch()

        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Поиск по ФИО, телефону, статусу...")
        self.edit_filter.setStyleSheet(
            "QLineEdit { border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; min-width: 260px; }")
        self.edit_filter.textChanged.connect(self._filter)
        cards.addWidget(self.edit_filter)

        btn_in = QPushButton("Ручной вход")
        btn_in.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        btn_in.clicked.connect(self._checkin)
        cards.addWidget(btn_in)
        btn = QPushButton("Обновить")
        btn.setStyleSheet(self._btn_secondary())
        btn.clicked.connect(self.refresh)
        cards.addWidget(btn)
        layout.addLayout(cards)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["№", "Клиент (ФИО)", "Телефон", "Способ входа", "Время входа", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        layout.addWidget(self.table)

    def _stat_card(self, title: str, value: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:24px; color:{theme.fg()};'>{value}</b><br>"
                     f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")
        lbl.setStyleSheet(theme.card_style())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _btn_secondary(self) -> str:
        return ("QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; "
                "border-radius: 6px; padding: 8px 16px; font-weight: 600; } "
                "QPushButton:hover { background: #e2e8f0; }")

    def refresh(self):
        self.worker = LoadVisitsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:24px; color:{theme.fg()};'>{value}</b><br>"
                    f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")

    def _on_loaded(self, visits: list, stats: dict, cmap: dict):
        self._all_data = visits
        self._cmap = cmap
        self._card(self.lbl_today, "Сегодня", stats.get("today", stats.get("today_count", 0)))
        self._card(self.lbl_week, "Неделя", stats.get("week", stats.get("week_count", 0)))
        self._card(self.lbl_month, "Месяц", stats.get("month", stats.get("month_count", 0)))
        self._render(visits)

    def _render(self, rows: list):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            fio, phone = self._cmap.get(str(row.get("client_id")), ("—", ""))
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(fio))
            self.table.setItem(i, 2, QTableWidgetItem(phone or "—"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("access_method") or "—")))
            tm = str(row.get("entry_time") or row.get("created_at") or "—")[:16].replace("T", " ")
            self.table.setItem(i, 4, QTableWidgetItem(tm))
            status = str(row.get("status") or "—")
            item = QTableWidgetItem(status)
            if status == "ACTIVE":
                item.setForeground(QColor("#059669"))
            elif status == "COMPLETED":
                item.setForeground(QColor("#64748b"))
            self.table.setItem(i, 5, item)
            self.table.setRowHeight(i, 28)

    def _filter(self, text: str):
        if not text:
            self._render(self._all_data)
            return
        t = text.lower()
        filtered = []
        for r in self._all_data:
            fio, phone = self._cmap.get(str(r.get("client_id")), ("", ""))
            hay = f"{fio} {phone} {r.get('status', '')} {r.get('access_method', '')}".lower()
            if t in hay:
                filtered.append(r)
        self._render(filtered)

    def _checkin(self):
        if not self._cmap:
            QMessageBox.warning(self, "Нет данных", "Список клиентов пуст")
            return
        options = [(f"{v[0]} ({v[1]})", k) for k, v in list(self._cmap.items())[:200]]
        dlg = FormDialog("Ручной вход клиента", [
            ("client_id", "Клиент *", "combo", options),
            ("access_method", "Способ", "combo",
             [("Ручной (ресепшен)", "manual"), ("Карта", "card"), ("QR", "qr"), ("Face ID", "face")]),
            ("zone", "Зона", "text", "main"),
        ], self)
        if dlg.exec() != FormDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        payload = {"client_id": v["client_id"],
                   "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "access_method": v["access_method"], "zone": v["zone"] or "main"}
        try:
            r = self.api.session.post(self.api._url("/visits/manual"), json=payload)
            r.raise_for_status()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка входа", str(e))

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
