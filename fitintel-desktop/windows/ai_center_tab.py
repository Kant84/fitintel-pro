# -*- coding: utf-8 -*-
"""AI Center: self-learning churn model UI."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox)
from windows.chart_widget import ChartWidget

class AICenterTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        if api is not None and not hasattr(api, "_e55_get") and hasattr(api, "api"):
            api = api.api
        self.api = api
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.lb_status = QLabel("Модель: —")
        self.lb_acc = QLabel("Точность: —")
        self.lb_samples = QLabel("Примеров: —")
        for lb in (self.lb_status, self.lb_acc, self.lb_samples):
            lb.setStyleSheet("color:#00f0ff; font-weight:bold; padding:4px;")
            row.addWidget(lb)
        lay.addLayout(row)

        ctl = QHBoxLayout()
        b1 = QPushButton("🎓 Обучить / дообучить"); b1.clicked.connect(self.train)
        b2 = QPushButton("📋 Список риска оттока"); b2.clicked.connect(self.load_risk)
        b3 = QPushButton("✅ Сверить прогнозы с фактом"); b3.clicked.connect(self.resolve)
        b4 = QPushButton("ℹ Статус модели"); b4.clicked.connect(self.load_status)
        for b in (b1, b2, b3, b4):
            ctl.addWidget(b)
        lay.addLayout(ctl)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Клиент ID", "Вероятность оттока", "Дней без визитов", "Визитов за 30 дн"])
        lay.addWidget(self.tbl)
        lay.addWidget(QLabel("Рост точности модели (каждое обучение — точка):"))
        self.chart = ChartWidget(); self.chart.setMinimumHeight(160)
        lay.addWidget(self.chart)

    def train(self):
        try:
            r = self.api._e55_post("/ai/churn/train", {})
            if r.get("ok"):
                QMessageBox.information(self, "AI", "Модель обучена! Примеров: %s, точность: %s" % (r.get("samples"), r.get("accuracy")))
                self.load_status()
            else:
                QMessageBox.warning(self, "AI", r.get("note") or r.get("error", "Ошибка обучения"))
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))

    def load_risk(self):
        try:
            r = self.api._e55_get("/ai/churn/predict?limit=50")
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

    def resolve(self):
        try:
            r = self.api._e55_post("/ai/churn/resolve", {})
            QMessageBox.information(self, "AI",
                "Сверено прогнозов: %s\nПроверенная точность: %s" % (r.get("resolved"), r.get("validated_accuracy")))
            self.load_status()
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))

    def load_status(self):
        try:
            r = self.api._e55_get("/ai/status")
            self.lb_status.setText("Модель: " + ("обучена (%s)" % r.get("trained_at", "")[:16] if r.get("trained") else "не обучена"))
            self.lb_acc.setText("Точность: %s" % (r.get("accuracy") if r.get("accuracy") is not None else "—"))
            self.lb_samples.setText("Примеров: %s" % r.get("samples", 0))
            hist = [(x["at"], x["accuracy"]) for x in r.get("accuracy_history", [])]
            self.chart.set_data(hist, [])
        except Exception as e:
            QMessageBox.critical(self, "AI", str(e))
