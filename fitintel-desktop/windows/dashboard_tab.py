"""FitIntel Pro — Dashboard/Analytics Tab"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient


class DashboardWorker(QThread):
    finished = pyqtSignal(dict, dict, dict, dict)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            dash = self.api.get_dashboard()
            churn = self.api.get_churn()
            segments = self.api.get_risk_segments()
            clients = self.api.get_clients()
            cmap = {}
            for c in clients:
                fio = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x)
                cmap[str(c.get("id"))] = fio or "—"
            self.finished.emit(dash, churn, segments, cmap)
        except Exception as e:
            self.error.emit(str(e))


RISK_COLORS = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}
RISK_LABELS = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}


class DashboardTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _card(self, title: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:22px; color:#0f172a;'>—</b><br>"
                     f"<span style='font-size:12px; color:#64748b;'>{title}</span>")
        lbl.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; min-width: 150px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _set_card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:22px; color:#0f172a;'>{value}</b><br>"
                    f"<span style='font-size:12px; color:#64748b;'>{title}</span>")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        row = QHBoxLayout()
        self.c_att = self._card("Посещений сегодня")
        self.c_rev = self._card("Выручка сегодня, ₽")
        self.c_forecast = self._card("Прогноз недели, ₽")
        self.c_churn = self._card("Клиентов в риске")
        self.c_vs = self._card("К прошлой неделе")
        for c in (self.c_att, self.c_rev, self.c_forecast, self.c_churn, self.c_vs):
            row.addWidget(c)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.lbl_segments = QLabel("Сегменты риска: —")
        self.lbl_segments.setStyleSheet("background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px; font-size: 13px;")
        layout.addWidget(self.lbl_segments)

        box = QGroupBox("AI: клиенты с риском оттока (топ-50)")
        bl = QVBoxLayout(box)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Клиент", "Балл риска", "Уровень", "Дней без визита", "Визитов за 30д", "Осталось дней абонемента"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        bl.addWidget(self.table)
        layout.addWidget(box)

    def refresh(self):
        self.worker = DashboardWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(lambda m: self.lbl_segments.setText(f"Ошибка: {m}"))
        self.worker.start()

    def _on_loaded(self, dash: dict, churn: dict, segments: dict, cmap: dict):
        self._set_card(self.c_att, "Посещений сегодня", dash.get("attendance_today", 0))
        self._set_card(self.c_rev, "Выручка сегодня, ₽", dash.get("revenue_today", 0))
        self._set_card(self.c_forecast, "Прогноз недели, ₽", dash.get("forecast_week_revenue", 0))
        self._set_card(self.c_churn, "Клиентов в риске", dash.get("churn_risk_count", 0))
        vs = dash.get("vs_last_week", "—")
        self._set_card(self.c_vs, "К прошлой неделе", vs)

        seg = segments.get("segments", {})
        if isinstance(seg, dict):
            txt = "  |  ".join(f"{RISK_LABELS.get(k, k)}: {v}" for k, v in seg.items())
        else:
            txt = str(seg)
        self.lbl_segments.setText(f"Сегменты риска:  {txt or '—'}   (всего: {segments.get('total', 0)})")

        items = churn.get("items", [])
        self.table.setRowCount(len(items))
        for i, r in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(cmap.get(str(r.get("client_id")), str(r.get("client_id", "—"))[:8])))
            self.table.setItem(i, 1, QTableWidgetItem(str(r.get("risk_score", 0))))
            lvl = str(r.get("risk_level", "—"))
            li = QTableWidgetItem(RISK_LABELS.get(lvl, lvl))
            li.setForeground(QColor(RISK_COLORS.get(lvl, "#0f172a")))
            self.table.setItem(i, 2, li)
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("days_since_visit", "—"))))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("visits_last_30d", "—"))))
            self.table.setItem(i, 5, QTableWidgetItem(str(r.get("subscription_days_left", "—"))))
