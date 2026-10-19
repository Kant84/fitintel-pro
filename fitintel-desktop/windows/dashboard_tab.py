# -*- coding: utf-8 -*-
"""Главная: обзор KPI, приток клиентов, полный прогноз (14 дн), тепловая карта, AI-отток."""
import json as _json
import requests as _rq
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer

from windows.chart_widget import ChartWidget, HeatmapWidget

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False

BASE_DEFAULT = "http://localhost:8001/api/v1"


class DashboardTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        if api is not None and not hasattr(api, "_e55_get") and hasattr(api, "api"):
            api = api.api
        self.api = api
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        lay.addWidget(self.tabs)
        self.tabs.addTab(self._overview_tab(), " Обзор")
        self.tabs.addTab(self._forecast_tab(), " Прогноз")
        self.tabs.addTab(self._heatmap_tab(), " Тепловая карта")
        self.tabs.addTab(self._ai_tab(), " AI Отток")
        QTimer.singleShot(60, self._autoload)

    def _autoload(self):
        self.load_overview()
        self.load_full_forecast()
        self.ai_status()

    # ---------- helpers ----------
    def _base(self):
        b = getattr(self.api, "base_url", None) or getattr(self.api, "base", None) or BASE_DEFAULT
        return str(b).rstrip("/")

    def _sess(self):
        s = getattr(self.api, "session", None)
        if s is not None:
            return s
        try:
            from paths import SETTINGS
            cfg = _json.load(open(SETTINGS, encoding="utf-8"))
            s = _rq.Session()
            s.headers["Authorization"] = "Bearer " + cfg.get("token", "")
            return s
        except Exception:
            return _rq

    def _get(self, path):
        r = self._sess().get(self._base() + path, timeout=60)
        r.raise_for_status()
        return r.json()

    def _post(self, path, payload=None):
        r = self._sess().post(self._base() + path, json=payload or {}, timeout=120)
        r.raise_for_status()
        return r.json()

    def _card(self, title, val_color="#00f0ff"):
        f = QFrame()
        f.setStyleSheet("QFrame { background:#0e0e1d; border:1px solid #ff2bd6; border-radius:8px; }")
        v = QVBoxLayout(f)
        val = QLabel("—")
        val.setStyleSheet("color:%s; font-size:22px; font-weight:bold; border:none;" % val_color)
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#9a9ac0; border:none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(val); v.addWidget(t)
        return f, val

    def _mini_fig(self):
        fig = Figure(figsize=(5, 2.2), tight_layout=True)
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor("#0e0e1d")
        ax.set_facecolor("#0e0e1d")
        for s in ax.spines.values():
            s.set_color("#333355")
        ax.tick_params(colors="#9a9ac0", labelsize=7)
        ax.title.set_color("#e8e8ff")
        ax.grid(color="#22223a", linewidth=0.8)
        ax.set_axisbelow(True)
        return fig, ax

    # ---------- tab 1: overview ----------
    def _overview_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        grid = QGridLayout()
        self.c_att_f, self.c_att = self._card("Посещений сегодня")
        self.c_rev_f, self.c_rev = self._card("Выручка сегодня, ₽", "#39ff14")
        self.c_new_f, self.c_new = self._card("Приток клиентов (мес.)", "#c084fc")
        self.c_out_f, self.c_out = self._card("Отток (мес.)", "#ff6b6b")
        self.c_fc_f, self.c_fc = self._card("Прогноз выручки +14 дн., ₽", "#ffd166")
        self.c_ch_f, self.c_ch = self._card("Клиентов в риске", "#ff5252")
        for i, f in enumerate((self.c_att_f, self.c_rev_f, self.c_new_f,
                               self.c_out_f, self.c_fc_f, self.c_ch_f)):
            f.setMinimumHeight(92)
            grid.addWidget(f, 0, i)
        v.addLayout(grid)
        self.lb_seg = QLabel("Сегменты риска: —")
        self.lb_seg.setStyleSheet("color:#39ff14; font-weight:bold; padding:6px;")
        v.addWidget(self.lb_seg)

        charts = QGridLayout()
        self._inflow_holder = QGridLayout()
        self._fc_holder = QGridLayout()
        charts.addLayout(self._inflow_holder, 0, 0)
        charts.addLayout(self._fc_holder, 0, 1)
        v.addLayout(charts, 1)

        row = QHBoxLayout()
        b1 = QPushButton(" Обновить"); b1.clicked.connect(self.load_overview)
        b2 = QPushButton(" Пересчитать историю (56 дн)"); b2.clicked.connect(self.recalc)
        row.addWidget(b1); row.addWidget(b2); row.addStretch(1)
        v.addLayout(row)
        return w

    def _set_canvas(self, holder, fig, title):
        while holder.count():
            it = holder.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        box = QFrame()
        box.setStyleSheet("QFrame{background:#0e0e1d;border:1px solid #ff2bd6;border-radius:8px;}")
        bl = QVBoxLayout(box)
        tl = QLabel(title)
        tl.setStyleSheet("color:#e8e8ff;font-weight:bold;border:none;")
        bl.addWidget(tl)
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bl.addWidget(canvas)
        holder.addWidget(box, 0, 0)

    def load_overview(self):
        ts = {}
        try:
            ts = self._get("/analytics/timeseries").get("series", {})
        except Exception:
            pass
        try:
            d = self._get("/analytics/dashboard?club_id=1")
            self.c_att.setText(str(d.get("attendance_today", "—")))
            self.c_rev.setText(str(d.get("revenue_today", "—")))
            self.c_ch.setText(str(d.get("churn_risk_count", "—")))
        except Exception:
            pass
        try:
            self.c_new.setText("{:,}".format(int(ts.get("new_clients", {}).get("total", 0))).replace(",", " "))
            self.c_out.setText("{:,}".format(int(ts.get("lost_clients", {}).get("total", 0))).replace(",", " "))
        except Exception:
            pass
        # приток по дням
        if _HAS_MPL:
            try:
                s = ts.get("new_clients", {})
                xs, ys = s.get("dates", []), s.get("values", [])
                fig, ax = self._mini_fig()
                ax.bar(range(len(xs)), ys, color="#c084fc", width=0.6)
                ax.set_xticks(range(0, len(xs), max(1, len(xs) // 8)))
                ax.set_xticklabels([xs[i][5:] for i in range(0, len(xs), max(1, len(xs) // 8))],
                                   rotation=45)
                ax.set_title("Приток клиентов по дням")
                self._set_canvas(self._inflow_holder, fig, "Приток клиентов по дням")
            except Exception:
                pass
        try:
            r = self._get("/ai/churn/predict?limit=500")
            rows = r.get("at_risk", [])
            hi = sum(1 for x in rows if x.get("churn_prob", 0) >= 0.66)
            mid = sum(1 for x in rows if 0.33 <= x.get("churn_prob", 0) < 0.66)
            lo = sum(1 for x in rows if x.get("churn_prob", 0) < 0.33)
            self.lb_seg.setText("Сегменты риска:  Низкий: %d  |  Средний: %d  |  Высокий: %d   (всего: %d)"
                                % (lo, mid, hi, len(rows)))
        except Exception:
            pass

    def load_full_forecast(self):
        if not _HAS_MPL:
            return
        total_fc = 0.0
        try:
            for i, (metric, title, color) in enumerate(
                    (("attendance", "Посещения — факт и прогноз", "#00f0ff"),
                     ("revenue", "Выручка — факт и прогноз", "#39ff14"))):
                r = self._get("/analytics/trend-forecast?metric=%s&days_ahead=14" % metric)
                hist = r.get("history", [])
                fore = r.get("forecast", [])
                fig, ax = self._mini_fig()
                xs = [h["d"][5:] for h in hist]
                ys = [h["value"] for h in hist]
                ax.plot(range(len(ys)), ys, color=color, linewidth=1.8, label="Факт")
                if fore and len(ys) >= 2:
                    fvals = [f["value"] for f in fore]
                    ax.plot(range(len(ys) - 1, len(ys) + len(fvals)), [ys[-1]] + fvals,
                            "--", color="#ff2bd6", linewidth=1.8, label="Прогноз")
                    ax.axvline(len(ys) - 1, color="#444466", lw=1)
                    if metric == "revenue":
                        total_fc = sum(fvals)
                ax.set_xticks(range(0, len(xs), max(1, len(xs) // 6)))
                ax.set_xticklabels([xs[i] for i in range(0, len(xs), max(1, len(xs) // 6))],
                                   rotation=45, fontsize=6)
                ax.set_title("%s  (тренд: %s)" % (title, r.get("trend", "?")))
                ax.legend(frameon=False, fontsize=7)
                holder = QGridLayout()
                self._fc_holder.addLayout(holder, 0, i)
                self._set_canvas(holder, fig, title)
            self.c_fc.setText("{:,}".format(int(round(total_fc))).replace(",", " "))
        except Exception:
            pass

    def recalc(self):
        try:
            self._post("/analytics/recalc?club_id=1&days=56")
            QMessageBox.information(self, "Пересчёт", "История пересчитана за 56 дней.")
            self._autoload()
        except Exception as e:
            QMessageBox.critical(self, "Пересчёт", str(e))

    # ---------- tab 2: forecast ----------
    def _forecast_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        sp = QSplitter(Qt.Orientation.Vertical)
        top = QWidget(); tv = QVBoxLayout(top)
        row = QHBoxLayout()
        row.addWidget(QLabel("Метрика:"))
        self.cb_m = QComboBox()
        for name, code in [("Посещаемость", "attendance"), ("Выручка", "revenue"),
                           ("Новые клиенты", "new_clients"), ("Риск оттока", "churn_risk")]:
            self.cb_m.addItem(name, code)
        row.addWidget(self.cb_m)
        row.addWidget(QLabel("Дней:"))
        self.sp_d = QSpinBox(); self.sp_d.setRange(1, 90); self.sp_d.setValue(7)
        row.addWidget(self.sp_d)
        b = QPushButton(" Построить прогноз"); b.clicked.connect(self.load_forecast)
        row.addWidget(b); row.addStretch(1)
        tv.addLayout(row)
        self.chart = ChartWidget()
        sp.addWidget(top); sp.addWidget(self.chart)
        sp.setStretchFactor(1, 1)
        v.addWidget(sp)
        return w

    def load_forecast(self):
        try:
            code = self.cb_m.currentData()
            r = self._post("/analytics/forecast?club_id=1", {"metric": code, "days_ahead": self.sp_d.value()})
            hist = [(x["date"], x["value"]) for x in r.get("history", [])]
            fore = [(x["date"], x["forecast"]) for x in r.get("forecast", [])]
            self.chart.set_data(hist, fore)
            if r.get("note"):
                QMessageBox.information(self, "Прогноз", r["note"])
        except Exception as e:
            QMessageBox.critical(self, "Прогноз", str(e))

    # ---------- tab 3: heatmap (matplotlib turbo) ----------
    def _heatmap_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        b = QPushButton(" Загрузить тепловую карту"); b.clicked.connect(self.load_heatmap)
        v.addWidget(b)
        self._hm_holder = QGridLayout()
        v.addLayout(self._hm_holder, 1)
        QTimer.singleShot(300, self.load_heatmap)
        return w

    def load_heatmap(self):
        if not _HAS_MPL:
            QMessageBox.warning(self, "Тепловая карта", "matplotlib не установлен")
            return
        try:
            r = self._get("/analytics/full-stats")
            rows = r.get("visits_wd_hour", [])
            wd_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            grid = [[0] * 24 for _ in range(7)]
            for x in rows:
                wd = int(x.get("wd") or 0); hr = int(x.get("hr") or 0)
                if 0 <= wd < 7 and 0 <= hr < 24:
                    grid[wd][hr] = int(x.get("cnt") or 0)
            fig = Figure(figsize=(11, 4.4), tight_layout=True)
            ax = fig.add_subplot(111)
            fig.patch.set_facecolor("#0e0e1d"); ax.set_facecolor("#0e0e1d")
            im = ax.imshow(grid, cmap="turbo", aspect="auto")
            ax.set_xticks(range(24))
            ax.set_xticklabels(range(24), color="#9a9ac0", fontsize=8)
            ax.set_yticks(range(7)); ax.set_yticklabels(wd_names, color="#9a9ac0", fontsize=9)
            for wd in range(7):
                for hr in range(24):
                    if grid[wd][hr]:
                        ax.text(hr, wd, str(grid[wd][hr]), ha="center", va="center",
                                fontsize=7, color="white")
            cb = fig.colorbar(im, ax=ax, shrink=0.85)
            cb.ax.tick_params(colors="#9a9ac0")
            cb.set_label("визитов", color="#9a9ac0")
            ax.set_title("Тепловая карта: день недели × час (цвет = число визитов)",
                         color="#e8e8ff", fontsize=11)
            for s in ax.spines.values():
                s.set_color("#333355")
            while self._hm_holder.count():
                it = self._hm_holder.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            canvas = FigureCanvas(fig)
            canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._hm_holder.addWidget(canvas, 0, 0)
        except Exception as e:
            QMessageBox.critical(self, "Тепловая карта", str(e))
    # ---------- tab 4: AI churn ----------
    def _ai_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        row = QHBoxLayout()
        b1 = QPushButton(" Обучить / дообучить"); b1.clicked.connect(self.ai_train)
        b2 = QPushButton(" Обновить список риска"); b2.clicked.connect(self.ai_load)
        b3 = QPushButton(" Сверить прогнозы с фактом"); b3.clicked.connect(self.ai_resolve)
        for b in (b1, b2, b3):
            row.addWidget(b)
        self.lb_ai = QLabel("Модель: —")
        self.lb_ai.setStyleSheet("color:#00f0ff; font-weight:bold;")
        row.addWidget(self.lb_ai); row.addStretch(1)
        v.addLayout(row)
        sp = QSplitter(Qt.Orientation.Vertical)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Клиент ID", "Вероятность оттока", "Дней без визитов", "Визитов за 30 дн"])
        sp.addWidget(self.tbl)
        bottom = QWidget(); bv = QVBoxLayout(bottom)
        bv.addWidget(QLabel("Рост точности модели:"))
        self.acc_chart = ChartWidget(); self.acc_chart.setMinimumHeight(140)
        bv.addWidget(self.acc_chart)
        sp.addWidget(bottom)
        sp.setStretchFactor(0, 2); sp.setStretchFactor(1, 1)
        v.addWidget(sp)
        return w

    def ai_train(self):
        try:
            r = self._post("/ai/churn/train")
            if r.get("ok"):
                QMessageBox.information(self, "AI", "Обучено! Примеров: %s, точность: %s" % (r.get("samples"), r.get("accuracy")))
                self.ai_status()
            else:
                QMessageBox.warning(self, "AI", r.get("note") or r.get("error", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))

    def ai_load(self):
        try:
            r = self._get("/ai/churn/predict?limit=100")
            rows = r.get("at_risk", [])
            self.tbl.setRowCount(len(rows))
            for i, x in enumerate(rows):
                self.tbl.setItem(i, 0, QTableWidgetItem(str(x.get("client_id"))))
                self.tbl.setItem(i, 1, QTableWidgetItem(str(x.get("churn_prob"))))
                self.tbl.setItem(i, 2, QTableWidgetItem(str(x.get("days_since_visit"))))
                self.tbl.setItem(i, 3, QTableWidgetItem(str(x.get("visits_30d"))))
            if not rows:
                QMessageBox.information(self, "AI", r.get("note", "Нет данных"))
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))

    def ai_resolve(self):
        try:
            r = self._post("/ai/churn/resolve")
            QMessageBox.information(self, "AI", "Сверено: %s, проверенная точность: %s" % (r.get("resolved"), r.get("validated_accuracy")))
            self.ai_status()
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))

    def ai_status(self):
        try:
            r = self._get("/ai/status")
            self.lb_ai.setText("Модель: %s | примеров: %s | точность: %s" % (
                "обучена" if r.get("trained") else "не обучена", r.get("samples", 0), r.get("accuracy")))
            hist = [(x["at"], x["accuracy"]) for x in r.get("accuracy_history", [])]
            self.acc_chart.set_data(hist, [])
        except Exception:
            pass


AnalyticsTab = DashboardTab