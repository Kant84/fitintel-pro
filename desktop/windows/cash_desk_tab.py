"""Cash Desk Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget, QInputDialog
from PyQt6.QtCore import Qt
from api.client import ApiClient


class CashDeskTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Cash Desk")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        btn_shift = QPushButton("Open Shift")
        btn_shift.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #34d399; }")
        btn_shift.clicked.connect(self._open_shift)
        actions.addWidget(btn_shift)
        btn_close = QPushButton("Close Shift")
        btn_close.setStyleSheet("QPushButton { background-color: #f59e0b; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #fbbf24; }")
        btn_close.clicked.connect(self._close_shift)
        actions.addWidget(btn_close)
        btn_sale = QPushButton("New Sale")
        btn_sale.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_sale.clicked.connect(self._new_sale)
        actions.addWidget(btn_sale)
        actions.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)
        self.lbl_shift = QLabel("Shift: Unknown")
        self.lbl_shift.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: bold; padding: 10px; background-color: #1e293b; border-radius: 6px; border: 1px solid #334155;")
        layout.addWidget(self.lbl_shift)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { background-color: #1e293b; color: #94a3b8; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; font-size: 12px; } QTabBar::tab:selected { background-color: #38bdf8; color: #0f172a; font-weight: bold; } QTabWidget::pane { border: none; background-color: #0f172a; }")
        self.tab_payments = QWidget()
        pl = QVBoxLayout(self.tab_payments)
        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(6)
        self.table_payments.setHorizontalHeaderLabels(["ID", "Client", "Amount", "Method", "Status", "Time"])
        self.table_payments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_payments.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        pl.addWidget(self.table_payments)
        self.tabs.addTab(self.tab_payments, "Payments")
        self.tab_receipts = QWidget()
        rl = QVBoxLayout(self.tab_receipts)
        self.table_receipts = QTableWidget()
        self.table_receipts.setColumnCount(5)
        self.table_receipts.setHorizontalHeaderLabels(["ID", "Payment", "Number", "Amount", "Time"])
        self.table_receipts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_receipts.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        rl.addWidget(self.table_receipts)
        self.tabs.addTab(self.tab_receipts, "Receipts")
        self.tab_wallet = QWidget()
        wl = QVBoxLayout(self.tab_wallet)
        self.lbl_balance = QLabel("Balance: -")
        self.lbl_balance.setStyleSheet("color: #38bdf8; font-size: 18px; font-weight: bold;")
        wl.addWidget(self.lbl_balance)
        self.table_wallet = QTableWidget()
        self.table_wallet.setColumnCount(4)
        self.table_wallet.setHorizontalHeaderLabels(["Time", "Type", "Amount", "Description"])
        self.table_wallet.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_wallet.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        wl.addWidget(self.table_wallet)
        self.tabs.addTab(self.tab_wallet, "Wallet")
        layout.addWidget(self.tabs)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            data = self.api.get_payments()
            if isinstance(data, list):
                self.table_payments.setRowCount(len(data))
                for i, row in enumerate(data):
                    if not isinstance(row, dict): continue
                    self.table_payments.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
                    self.table_payments.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", "-"))))
                    self.table_payments.setItem(i, 2, QTableWidgetItem(str(row.get("amount", "-"))))
                    self.table_payments.setItem(i, 3, QTableWidgetItem(str(row.get("method", "-"))))
                    self.table_payments.setItem(i, 4, QTableWidgetItem(str(row.get("status", "-"))))
                    self.table_payments.setItem(i, 5, QTableWidgetItem(str(row.get("created_at", "-"))[:16]))
        except Exception as e: self.lbl_status.setText("Payments error: " + str(e)[:80])
        try:
            data = self.api.get_receipts()
            if isinstance(data, list):
                self.table_receipts.setRowCount(len(data))
                for i, row in enumerate(data):
                    if not isinstance(row, dict): continue
                    self.table_receipts.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
                    self.table_receipts.setItem(i, 1, QTableWidgetItem(str(row.get("payment_id", "-"))))
                    self.table_receipts.setItem(i, 2, QTableWidgetItem(str(row.get("receipt_number", "-"))))
                    self.table_receipts.setItem(i, 3, QTableWidgetItem(str(row.get("amount", "-"))))
                    self.table_receipts.setItem(i, 4, QTableWidgetItem(str(row.get("created_at", "-"))[:16]))
        except Exception: pass
        try:
            bal = self.api.get_balance()
            if isinstance(bal, dict): self.lbl_balance.setText("Balance: " + str(bal.get("balance", "-")) + " rub")
        except Exception: pass
        try:
            txs = self.api.get_transactions()
            if isinstance(txs, list):
                self.table_wallet.setRowCount(len(txs))
                for i, row in enumerate(txs):
                    if not isinstance(row, dict): continue
                    self.table_wallet.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", "-"))[:16]))
                    self.table_wallet.setItem(i, 1, QTableWidgetItem(str(row.get("type", "-"))))
                    self.table_wallet.setItem(i, 2, QTableWidgetItem(str(row.get("amount", "-"))))
                    self.table_wallet.setItem(i, 3, QTableWidgetItem(str(row.get("description", "-"))))
        except Exception: pass

    def _open_shift(self):
        try:
            result = self.api.open_shift({"cashier_id": str(self.user.get("id", ""))})
            QMessageBox.information(self, "Success", "Shift opened: " + str(result.get("shift_id", "OK")))
        except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])

    def _close_shift(self):
        try:
            result = self.api.close_shift({"cashier_id": str(self.user.get("id", ""))})
            QMessageBox.information(self, "Success", "Shift closed. Revenue: " + str(result.get("revenue", "-")))
        except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])

    def _new_sale(self):
        text, ok = QInputDialog.getText(self, "New Sale", "client_id, item, amount:")
        if ok and text:
            parts = text.split(",")
            if len(parts) >= 3:
                try:
                    result = self.api.create_sale({"client_id": parts[0].strip(), "item": parts[1].strip(), "amount": float(parts[2].strip()), "cashier_id": str(self.user.get("id", ""))})
                    QMessageBox.information(self, "Success", "Sale: " + str(result.get("sale_id", "OK")))
                    self.refresh()
                except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])
            else: QMessageBox.warning(self, "Error", "Format: client_id, item, amount")
