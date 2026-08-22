"""FitIntel Pro — Dashboard/Analytics Tab (графики + AI)"""
import tempfile
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class AnalyticsWorker(QThread):
    finished = pyqtSignal(dict, dict, dict, dict, dict, dict)
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
            forecast = {}
            try:
                r = self.api.session.post(self.api._url("/analytics/forecast"),
                                          json={"metric": "revenue", "days_ahead": 7})
                if r.status_code == 200:
                    forecast = r.json()
            except Exception:
                pass
            heatmap = {}
            try:
                r = self.api.session.get(self.api._url("/analytics/ai/heatmap"))
                if r.status_code == 200:
                    heatmap = r.json()
            except Exception:
                pass
            self.finished.emit(dash, churn, segments, cmap, forecast, heatmap)
        except Exception as e:
            self.error.emit(str(e))


RISK_COLORS = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}
RISK_LABELS = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


class DashboardTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._build_ui()
        self.refresh()

    def _card(self, title: str) -> QLabel:
        lbl = QLabel(f"<b style='font-size:22px; color:{theme.fg()};'>—</b><br>"
                     f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")
        lbl.setStyleSheet(theme.card_style())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _set_card(self, lbl: QLabel, title: str, value):
        lbl.setText(f"<b style='font-size:22px; color:{theme.fg()};'>{value}</b><br>"
                    f"<span style='font-size:12px; color:{theme.sub()};'>{title}</span>")

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
        b_web = QPushButton("Веб-график")
        b_web.setToolTip("Открыть интерактивный HTML-дашборд в браузере")
        b_web.setStyleSheet("QPushButton { background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        b_web.clicked.connect(self._open_web)
        row.addWidget(b_web)
        btn = QPushButton("Обновить")
        btn.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn.clicked.connect(self.refresh)
        row.addWidget(btn)
        layout.addLayout(row)

        self.lbl_segments = QLabel("Сегменты риска: —")
        self.lbl_segments.setStyleSheet(theme.banner_style())
        layout.addWidget(self.lbl_segments)

        # ── графики ──
        box = QGroupBox("Выручка (история + прогноз)  |  Тепловая карта посещений")
        gl = QVBoxLayout(box)
        self.fig = Figure(figsize=(10, 3.2), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(260)
        gl.addWidget(self.canvas)
        layout.addWidget(box)

        box2 = QGroupBox("AI: клиенты с риском оттока (топ-50)")
        bl = QVBoxLayout(box2)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Клиент", "Балл риска", "Уровень", "Дней без визита", "Визитов за 30д", "Осталось дней абонемента"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        bl.addWidget(self.table)
        layout.addWidget(box2)

    def refresh(self):
        self.worker = AnalyticsWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(lambda m: self.lbl_segments.setText(f"Ошибка: {m}"))
        self.worker.start()

    def _draw_charts(self, forecast: dict, heatmap: dict):
        dark = theme.is_dark()
        bg = "#1e293b" if dark else "#ffffff"
        fg = "#e2e8f0" if dark else "#0f172a"
        grid_c = "#334155" if dark else "#e2e8f0"
        self.fig.clear()
        self.fig.patch.set_facecolor(bg)

        # график выручки
        ax1 = self.fig.add_subplot(121)
        ax1.set_facecolor(bg)
        history = forecast.get("history", [])
        if history:
            dates = [h["date"][5:] for h in history]
            values = [h["value"] for h in history]
            is_f = [h.get("is_forecast") for h in history]
            hist_x = [i for i, f in enumerate(is_f) if not f]
            fore_x = [i for i, f in enumerate(is_f) if f]
            if hist_x:
                ax1.plot(hist_x, [values[i] for i in hist_x], color="#10b981", lw=2, label="Факт")
            if fore_x:
                fx = [hist_x[-1]] + fore_x if hist_x else fore_x
                fv = [values[hist_x[-1]]] + [values[i] for i in fore_x] if hist_x else [values[i] for i in fore_x]
                ax1.plot(fx, fv, color="#f59e0b", lw=2, ls="--", marker="o", ms=4, label="Прогноз")
            step = max(1, len(dates) // 8)
            ax1.set_xticks(range(0, len(dates), step))
            ax1.set_xticklabels([dates[i] for i in range(0, len(dates), step)],
                                rotation=45, fontsize=7, color=fg)
            ax1.legend(fontsize=8, facecolor=bg, labelcolor=fg)
        else:
            ax1.text(0.5, 0.5, "Нет данных прогноза", ha="center", color=fg)
        ax1.set_title("Выручка, ₽", color=fg, fontsize=10)
        ax1.tick_params(colors=fg)
        ax1.grid(color=grid_c, alpha=0.5)
        for s in ax1.spines.values():
            s.set_color(grid_c)

        # тепловая карта
        ax2 = self.fig.add_subplot(122)
        grid = [[0] * 24 for _ in range(7)]
        for cell in heatmap.get("grid", []):
            wd, hr = cell.get("weekday", 0), cell.get("hour", 0)
            if 0 <= wd < 7 and 0 <= hr < 24:
                grid[wd][hr] = cell.get("count", 0)
        im = ax2.imshow(grid, aspect="auto", cmap="YlOrRd")
        ax2.set_yticks(range(7))
        ax2.set_yticklabels(WEEKDAYS, fontsize=8, color=fg)
        ax2.set_xticks(range(0, 24, 3))
        ax2.set_xticklabels([f"{h}:00" for h in range(0, 24, 3)], fontsize=7, color=fg)
        ax2.set_title("Посещения: день недели × час", color=fg, fontsize=10)
        self.fig.colorbar(im, ax=ax2, shrink=0.8)

        self.canvas.draw()

    def _open_web(self):
        try:
            r = self.api.session.get(self.api._url("/analytics/dashboard-chart"))
            r.raise_for_status()
            path = os.path.join(tempfile.gettempdir(), "fitintel_dashboard.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(r.text)
            os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_loaded(self, dash: dict, churn: dict, segments: dict, cmap: dict,
                   forecast: dict, heatmap: dict):
        self._set_card(self.c_att, "Посещений сегодня", dash.get("attendance_today", 0))
        self._set_card(self.c_rev, "Выручка сегодня, ₽", dash.get("revenue_today", 0))
        self._set_card(self.c_forecast, "Прогноз недели, ₽", dash.get("forecast_week_revenue", 0))
        self._set_card(self.c_churn, "Клиентов в риске", dash.get("churn_risk_count", 0))
        self._set_card(self.c_vs, "К прошлой неделе", dash.get("vs_last_week", "—"))

        seg = segments.get("segments", {})
        txt = "  |  ".join(f"{RISK_LABELS.get(k, k)}: {v}" for k, v in seg.items()) if isinstance(seg, dict) else str(seg)
        self.lbl_segments.setText(f"Сегменты риска:  {txt or '—'}   (всего: {segments.get('total', 0)})")

        self._draw_charts(forecast, heatmap)

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
