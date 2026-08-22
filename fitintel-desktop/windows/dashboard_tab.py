# -*- coding: utf-8 -*-
"""Analytics screen: sub-tabs (Overview / Forecast / Heatmap / AI churn), movable tabs, splitters."""
import requests as _rq
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QFrame)
from PyQt6.QtCore import Qt
from windows.chart_widget import ChartWidget, HeatmapWidget

BASE_DEFAULT = "http://localhost:8001/api/v1"

class DashboardTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        if api is not None and not hasattr(api, "_e55_get") and hasattr(api, "api"):
            api = api.api
        self.api = api
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)  # вкладки можно перетаскивать местами
        lay.addWidget(self.tabs)
        self.tabs.addTab(self._overview_tab(), "📊 Обзор")
        self.tabs.addTab(self._forecast_tab(), "📈 Прогноз")
        self.tabs.addTab(self._heatmap_tab(), "🔥 Тепловая карта")
        self.tabs.addTab(self._ai_tab(), "🤖 AI Отток")

    # ---------- helpers ----------
    def _base(self):
        b = getattr(self.api, "base_url", None) or getattr(self.api, "base", None) or BASE_DEFAULT
        return str(b).rstrip("/")

    def _get(self, path):
        r = _rq.get(self._base() + path, timeout=60)
        r.raise_for_status()
        return r.json()

    def _post(self, path, payload=None):
        r = _rq.post(self._base() + path, json=payload or {}, timeout=120)
        r.raise_for_status()
        return r.json()

    def _card(self, title):
        f = QFrame()
        f.setStyleSheet("QFrame { background:#0e0e1d; border:1px solid #ff2bd6; border-radius:8px; }")
        v = QVBoxLayout(f)
        val = QLabel("—")
        val.setStyleSheet("color:#00f0ff; font-size:24px; font-weight:bold; border:none;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#9a9ac0; border:none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(val); v.addWidget(t)
        return f, val

    # ---------- tab 1: overview ----------
    def _overview_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        grid = QGridLayout()
        self.c_att_f, self.c_att = self._card("Посещений сегодня")
        self.c_rev_f, self.c_rev = self._card("Выручка сегодня, ₽")
        self.c_fc_f, self.c_fc = self._card("Прогноз недели, ₽")
        self.c_ch_f, self.c_ch = self._card("Клиентов в риске")
        self.c_vs_f, self.c_vs = self._card("К прошлой неделе, %")
        for i, f in enumerate((self.c_att_f, self.c_rev_f, self.c_fc_f, self.c_ch_f, self.c_vs_f)):
            f.setMinimumHeight(90)
            grid.addWidget(f, 0, i)
        v.addLayout(grid)
        self.lb_seg = QLabel("Сегменты риска: —")
        self.lb_seg.setStyleSheet("color:#39ff14; font-weight:bold; padding:6px;")
        v.addWidget(self.lb_seg)
        row = QHBoxLayout()
        b1 = QPushButton("🔄 Обновить"); b1.clicked.connect(self.load_overview)
        b2 = QPushButton("🧮 Пересчитать историю (56 дн)"); b2.clicked.connect(self.recalc)
        row.addWidget(b1); row.addWidget(b2); row.addStretch(1)
        v.addLayout(row)
        v.addStretch(1)
        return w

    def load_overview(self):
        try:
            d = self._get("/analytics/dashboard?club_id=1")
            self.c_att.setText(str(d.get("attendance_today", "—")))
            self.c_rev.setText(str(d.get("revenue_today", "—")))
            self.c_fc.setText(str(d.get("forecast_week_revenue", "—")))
            self.c_ch.setText(str(d.get("churn_risk_count", "—")))
            self.c_vs.setText(str(d.get("vs_last_week", "—")))
        except Exception as e:
            QMessageBox.critical(self, "Обзор", str(e))
        try:
            r = self._get("/ai/churn/predict?limit=500")
            rows = r.get("at_risk", [])
            hi = sum(1 for x in rows if x.get("churn_prob", 0) >= 0.66)
            mid = sum(1 for x in rows if 0.33 <= x.get("churn_prob", 0) < 0.66)
            lo = sum(1 for x in rows if x.get("churn_prob", 0) < 0.33)
            self.lb_seg.setText("Сегменты риска:  Низкий: %d  |  Средний: %d  |  Высокий: %d   (всего: %d)" % (lo, mid, hi, len(rows)))
        except Exception:
            pass

    def recalc(self):
        try:
            r = self._post("/analytics/recalc?club_id=1&days=56")
            QMessageBox.information(self, "Пересчёт", "История пересчитана за 56 дней.")
            self.load_overview()
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
        b = QPushButton("📈 Построить прогноз"); b.clicked.connect(self.load_forecast)
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

    # ---------- tab 3: heatmap ----------
    def _heatmap_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        b = QPushButton("🔄 Загрузить тепловую карту"); b.clicked.connect(self.load_heatmap)
        v.addWidget(b)
        self.hm = HeatmapWidget()
        v.addWidget(self.hm)
        return w

    def load_heatmap(self):
        try:
            r = self._get("/analytics/heatmap?club_id=1")
            if r.get("ok"):
                self.hm.set_grid(r["grid"])
            else:
                QMessageBox.warning(self, "Тепловая карта", str(r.get("error", "нет данных")))
        except Exception as e:
            QMessageBox.critical(self, "Тепловая карта", str(e))

    # ---------- tab 4: AI churn ----------
    def _ai_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        row = QHBoxLayout()
        b1 = QPushButton("🎓 Обучить / дообучить"); b1.clicked.connect(self.ai_train)
        b2 = QPushButton("📋 Обновить список риска"); b2.clicked.connect(self.ai_load)
        b3 = QPushButton("✅ Сверить прогнозы с фактом"); b3.clicked.connect(self.ai_resolve)
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
