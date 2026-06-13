"""Subscriptions Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout, QComboBox, QDateEdit
from PyQt6.QtCore import Qt, QDate
from api.client import ApiClient


class SubEditDialog(QDialog):
    def __init__(self, api, sub=None, tariffs=None, clients=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Subscription" if sub else "New Subscription")
        self.setMinimumWidth(450)
        self.setStyleSheet("QDialog { background-color: #1e293b; } QLabel { color: #e2e8f0; font-size: 13px; } QLineEdit, QComboBox, QDateEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; } QPushButton#cancel { background-color: transparent; color: #94a3b8; border: 1px solid #475569; } QPushButton#cancel:hover { background-color: #334155; }")
        self._build_ui(sub or {}, tariffs or [], clients or [])

    def _build_ui(self, sub, tariffs, clients):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        form.setSpacing(10)
        self.cmb_client = QComboBox()
        for c in clients: self.cmb_client.addItem(str(c.get("name", "-")) + " (" + str(c.get("id", "-"))[:8] + ")", c.get("id"))
        form.addRow("Client *", self.cmb_client)
        self.cmb_tariff = QComboBox()
        for t in tariffs: self.cmb_tariff.addItem(str(t.get("name", "-")), t.get("id"))
        form.addRow("Tariff *", self.cmb_tariff)
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate())
        form.addRow("Start Date", self.dt_start)
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate().addMonths(1))
        form.addRow("End Date", self.dt_end)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["active", "frozen", "expired"])
        form.addRow("Status", self.cmb_status)
        layout.addLayout(form)
        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _save(self):
        self.data = {"client_id": str(self.cmb_client.currentData()), "tariff_id": str(self.cmb_tariff.currentData()), "start_date": self.dt_start.date().toString("yyyy-MM-dd"), "end_date": self.dt_end.date().toString("yyyy-MM-dd"), "status": self.cmb_status.currentText()}
        self.accept()

    def get_data(self):
        return getattr(self, "data", {})


class SubscriptionsTab(QWidget):
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
        title = QLabel("Subscriptions")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by client or tariff...")
        self.txt_search.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_search.textChanged.connect(self._filter)
        toolbar.addWidget(self.txt_search)
        toolbar.addStretch()
        btn_add = QPushButton("+ New Subscription")
        btn_add.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #34d399; }")
        btn_add.clicked.connect(self._add_sub)
        toolbar.addWidget(btn_add)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Client", "Tariff", "Start", "End", "Status", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.lbl_status = QLabel("Loading...")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            self._all_data = self.api.get_subscriptions()
            if not isinstance(self._all_data, list): self._all_data = []
            self._populate_table(self._all_data)
            self.lbl_status.setText("Total subscriptions: " + str(len(self._all_data)))
        except Exception as e:
            self.lbl_status.setText("Error: " + str(e)[:100])

    def _populate_table(self, data):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", row.get("client_id", "-")))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("tariff_name", row.get("tariff_id", "-")))))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("start_date", "-"))[:10]))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("end_date", "-"))[:10]))
            self.table.setItem(i, 5, QTableWidgetItem(str(row.get("status", "-"))))
            self.table.setItem(i, 6, QTableWidgetItem("Freeze | Extend"))

    def _filter(self, text):
        text = text.lower()
        if not text: self._populate_table(self._all_data); return
        filtered = [r for r in self._all_data if isinstance(r, dict) and (text in str(r.get("client_name", "")).lower() or text in str(r.get("tariff_name", "")).lower())]
        self._populate_table(filtered)

    def _add_sub(self):
        dlg = SubEditDialog(self.api, None, [], [], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_subscription(dlg.get_data())
                QMessageBox.information(self, "Success", "Subscription created")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e)[:200])
