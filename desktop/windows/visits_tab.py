"""Visits Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGridLayout, QFrame, QInputDialog
from PyQt6.QtCore import Qt, QTimer
from api.client import ApiClient


class StatCard(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 12px; }")
        l = QVBoxLayout(self)
        t = QLabel(title)
        t.setStyleSheet("color: #94a3b8; font-size: 12px;")
        l.addWidget(t)
        self.v = QLabel(value)
        self.v.setStyleSheet("color: " + color + "; font-size: 24px; font-weight: bold;")
        l.addWidget(self.v)

    def set_value(self, val):
        self.v.setText(str(val))


class VisitsTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._all_data = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Visits Control")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        btn_entry = QPushButton("Entry (Check-in)")
        btn_entry.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #34d399; }")
        btn_entry.clicked.connect(self._entry)
        actions.addWidget(btn_entry)
        btn_exit = QPushButton("Exit (Check-out)")
        btn_exit.setStyleSheet("QPushButton { background-color: #f59e0b; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #fbbf24; }")
        btn_exit.clicked.connect(self._exit)
        actions.addWidget(btn_exit)
        btn_manual = QPushButton("Manual Visit")
        btn_manual.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 10px 20px; font-size: 14px; } QPushButton:hover { background-color: #64748b; }")
        btn_manual.clicked.connect(self._manual)
        actions.addWidget(btn_manual)
        actions.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.card_active = StatCard("Active Now", "-", "#10b981")
        self.card_today = StatCard("Today", "-", "#38bdf8")
        self.card_week = StatCard("This Week", "-", "#8b5cf6")
        self.card_month = StatCard("This Month", "-", "#f59e0b")
        stats.addWidget(self.card_active, 0, 0)
        stats.addWidget(self.card_today, 0, 1)
        stats.addWidget(self.card_week, 0, 2)
        stats.addWidget(self.card_month, 0, 3)
        layout.addLayout(stats)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by client name or card...")
        self.txt_search.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_search.textChanged.connect(self._filter)
        layout.addWidget(self.txt_search)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Time", "Client", "Action", "Location", "Duration", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.lbl_status = QLabel("Loading...")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30000)

    def refresh(self):
        try:
            try:
                stats = self.api.get_visit_stats()
                if isinstance(stats, dict):
                    self.card_active.set_value(stats.get("active_now", 0))
                    self.card_today.set_value(stats.get("today", 0))
                    self.card_week.set_value(stats.get("week", 0))
                    self.card_month.set_value(stats.get("month", 0))
            except Exception: pass
            data = self.api.get_visits()
            if isinstance(data, list): self._all_data = data
            elif isinstance(data, dict) and "items" in data: self._all_data = data["items"]
            else: self._all_data = []
            self._populate_table(self._all_data)
            self.lbl_status.setText("Visits: " + str(len(self._all_data)))
        except Exception as e:
            self.lbl_status.setText("Error: " + str(e)[:100])

    def _populate_table(self, data):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", "-"))[:16]))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", row.get("client_id", "-")))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("action", "-")).upper()))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("location", "-"))))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("duration", "-"))))
            self.table.setItem(i, 5, QTableWidgetItem(str(row.get("status", "-"))))

    def _filter(self, text):
        text = text.lower()
        if not text: self._populate_table(self._all_data); return
        filtered = [r for r in self._all_data if isinstance(r, dict) and (text in str(r.get("client_name", "")).lower() or text in str(r.get("card_number", "")).lower())]
        self._populate_table(filtered)

    def _entry(self):
        text, ok = QInputDialog.getText(self, "Entry", "Enter client card or ID:")
        if ok and text:
            try:
                result = self.api.entry_visit({"credential": text.strip(), "location": "reception"})
                QMessageBox.information(self, "Success", str(result.get("message", "OK")))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e)[:200])

    def _exit(self):
        text, ok = QInputDialog.getText(self, "Exit", "Enter client card or ID:")
        if ok and text:
            try:
                result = self.api.exit_visit({"credential": text.strip()})
                QMessageBox.information(self, "Success", str(result.get("message", "OK")))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e)[:200])

    def _manual(self):
        text, ok = QInputDialog.getText(self, "Manual Visit", "client_id, duration_minutes:")
        if ok and text:
            parts = text.split(",")
            if len(parts) >= 2:
                try:
                    self.api.entry_visit({"client_id": parts[0].strip(), "duration_minutes": int(parts[1].strip()), "location": "manual", "action": "manual"})
                    QMessageBox.information(self, "Success", "Manual visit recorded")
                    self.refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e)[:200])
            else:
                QMessageBox.warning(self, "Error", "Format: client_id, duration_minutes")
