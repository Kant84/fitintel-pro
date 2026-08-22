# -*- coding: utf-8 -*-
"""E16: Analytics dashboard + forecast chart (TZ v3.4 §4.28)."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QMessageBox)
from PyQt6.QtCore import Qt
from windows.chart_widget import ChartWidget

METRICS = [("Посещаемость", "attendance"), ("Выручка", "revenue"),
           ("Новые клиенты", "new_clients"), ("Риск оттока", "churn_risk")]

class AnalyticsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        if api is not None and not hasattr(api, "_e55_get") and hasattr(api, "api"):
            api = api.api
        self.api = api
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.lb_att = QLabel("Посещаемость сегодня: —")
        self.lb_rev = QLabel("Выручка сегодня: —")
        self.lb_churn = QLabel("Риск оттока: —")
        self.lb_fc = QLabel("Прогноз выручки на неделю: —")
        self.lb_vs = QLabel("К прошлой неделе: —")
        for lb in (self.lb_att, self.lb_rev, self.lb_churn, self.lb_fc, self.lb_vs):
            lb.setStyleSheet("color:#00f0ff; font-weight:bold; padding:4px;")
            row.addWidget(lb)
        lay.addLayout(row)

        ctl = QHBoxLayout()
        self.cb_metric = QComboBox()
        for name, _code in METRICS:
            self.cb_metric.addItem(name)
        ctl.addWidget(self.cb_metric)
        ctl.addWidget(QLabel("Дней прогноза:"))
        self.sp_days = QSpinBox(); self.sp_days.setRange(1, 90); self.sp_days.setValue(7)
        ctl.addWidget(self.sp_days)
        b1 = QPushButton("🔄 Обновить дашборд"); b1.clicked.connect(self.load_dashboard)
        b2 = QPushButton("🧮 Пересчитать историю (56 дн)"); b2.clicked.connect(self.recalc)
        b3 = QPushButton("📈 Построить прогноз"); b3.clicked.connect(self.load_forecast)
        for b in (b1, b2, b3):
            ctl.addWidget(b)
        lay.addLayout(ctl)

        self.chart = ChartWidget()
        lay.addWidget(self.chart)

    def _metric_code(self):
        return METRICS[self.cb_metric.currentIndex()][1]

    def load_dashboard(self):
        try:
            d = self.api._e55_get("/analytics/dashboard?club_id=1")
            self.lb_att.setText("Посещаемость сегодня: %s" % d.get("attendance_today", "—"))
            self.lb_rev.setText("Выручка сегодня: %s ₽" % d.get("revenue_today", "—"))
            self.lb_churn.setText("Риск оттока: %s" % d.get("churn_risk_count", "—"))
            self.lb_fc.setText("Прогноз недели: %s ₽" % d.get("forecast_week_revenue", "—"))
            vs = d.get("vs_last_week", 0)
            arrow = "▲" if (vs or 0) >= 0 else "▼"
            self.lb_vs.setText("К прошлой неделе: %s %s%%" % (arrow, vs))
        except Exception as e:
            QMessageBox.critical(self, "Аналитика", str(e))

    def recalc(self):
        try:
            r = self.api._e55_post("/analytics/recalc?club_id=1&days=56", {})
            QMessageBox.information(self, "Аналитика", "История пересчитана: " + str(r.get("metrics", "")))
            self.load_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Аналитика", str(e))

    def load_forecast(self):
        try:
            r = self.api._e55_post("/analytics/forecast?club_id=1",
                {"metric": self._metric_code(), "days_ahead": self.sp_days.value()})
            hist = [(x["date"], x["value"]) for x in r.get("history", [])]
            fore = [(x["date"], x["forecast"]) for x in r.get("forecast", [])]
            if not fore and r.get("note"):
                QMessageBox.information(self, "Прогноз", r["note"])
            self.chart.set_data(hist, fore)
        except Exception as e:
            QMessageBox.critical(self, "Прогноз", str(e))
