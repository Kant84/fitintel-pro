"""Analytics Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from api.client import ApiClient


class StatCard(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 16px; }")
        l = QVBoxLayout(self)
        t = QLabel(title)
        t.setStyleSheet("color: #94a3b8; font-size: 13px;")
        l.addWidget(t)
        self.v = QLabel(value)
        self.v.setStyleSheet("color: " + color + "; font-size: 28px; font-weight: bold;")
        self.v.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        l.addWidget(self.v)
    def set_value(self, value): self.v.setText(str(value))


class AnalyticsTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        title = QLabel("Dashboard")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_refresh.clicked.connect(self.refresh)
        header = QHBoxLayout()
        header.addStretch()
        header.addWidget(btn_refresh)
        layout.addLayout(header)
        cards = QGridLayout()
        cards.setSpacing(16)
        self.card_clients = StatCard("Total Clients", "-", "#38bdf8")
        self.card_active = StatCard("Active Now", "-", "#10b981")
        self.card_visits = StatCard("Visits Today", "-", "#8b5cf6")
        self.card_revenue = StatCard("Revenue Today", "-", "#f59e0b")
        cards.addWidget(self.card_clients, 0, 0)
        cards.addWidget(self.card_active, 0, 1)
        cards.addWidget(self.card_visits, 0, 2)
        cards.addWidget(self.card_revenue, 0, 3)
        layout.addLayout(cards)
        sec = QLabel("Recent Activity")
        sec.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(sec)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Event", "Client", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60000)

    def refresh(self):
        try:
            try:
                clients = self.api.get_clients()
                client_count = len(clients) if isinstance(clients, list) else 0
            except: client_count = 0
            try:
                visits = self.api.get_visit_stats()
                if isinstance(visits, dict):
                    today_visits = visits.get("today", 0)
                    active_now = visits.get("active_now", 0)
                    revenue = visits.get("revenue_today", 0)
                else: today_visits = 0; active_now = 0; revenue = 0
            except: today_visits = 0; active_now = 0; revenue = 0
            self.card_clients.set_value(client_count)
            self.card_active.set_value(active_now)
            self.card_visits.set_value(today_visits)
            self.card_revenue.set_value(str(revenue) + " rub")
            try:
                visit_list = self.api.get_visits()
                if isinstance(visit_list, list):
                    self.table.setRowCount(min(len(visit_list), 20))
                    for i, v in enumerate(visit_list[:20]):
                        if not isinstance(v, dict): continue
                        self.table.setItem(i, 0, QTableWidgetItem(str(v.get("timestamp", "-"))[:16]))
                        self.table.setItem(i, 1, QTableWidgetItem(v.get("action", "-").upper()))
                        self.table.setItem(i, 2, QTableWidgetItem(str(v.get("client_name", "-"))))
                        self.table.setItem(i, 3, QTableWidgetItem(v.get("details", "-")))
                else: self.table.setRowCount(0)
            except: self.table.setRowCount(0)
        except: pass
