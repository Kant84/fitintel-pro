"""Access Control Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt
from api.client import ApiClient


class AccessTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._all_creds = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Access Control")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        cf = QWidget()
        cf.setStyleSheet("QWidget { background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 12px; }")
        ch = QHBoxLayout(cf)
        ch.setSpacing(12)
        ch.addWidget(QLabel("Quick Check:") if True else None)
        lbl = QLabel("Quick Check:")
        lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        ch.addWidget(lbl)
        self.txt_check = QLineEdit()
        self.txt_check.setPlaceholderText("Enter QR code or RFID...")
        self.txt_check.setStyleSheet("QLineEdit { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_check.returnPressed.connect(self._quick_check)
        ch.addWidget(self.txt_check, 1)
        btn_check = QPushButton("Check Access")
        btn_check.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_check.clicked.connect(self._quick_check)
        ch.addWidget(btn_check)
        layout.addWidget(cf)

        self.lbl_result = QLabel("Enter credential to check access")
        self.lbl_result.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; padding: 12px; background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_result)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        btn_qr = QPushButton("Generate QR")
        btn_qr.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #34d399; }")
        btn_qr.clicked.connect(self._gen_qr)
        actions.addWidget(btn_qr)
        btn_rfid = QPushButton("Generate RFID")
        btn_rfid.setStyleSheet("QPushButton { background-color: #8b5cf6; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #a78bfa; }")
        btn_rfid.clicked.connect(self._gen_rfid)
        actions.addWidget(btn_rfid)
        btn_block = QPushButton("Block")
        btn_block.setStyleSheet("QPushButton { background-color: #f59e0b; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #fbbf24; }")
        btn_block.clicked.connect(self._block)
        actions.addWidget(btn_block)
        btn_unblock = QPushButton("Unblock")
        btn_unblock.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_unblock.clicked.connect(self._unblock)
        actions.addWidget(btn_unblock)
        actions.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search credentials by client...")
        self.txt_search.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_search.textChanged.connect(self._filter)
        layout.addWidget(self.txt_search)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Client", "Type", "Code", "Status", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            data = self.api._get("/credentials/")
            if isinstance(data, list): self._all_creds = data
            else: self._all_creds = []
            self._populate_table(self._all_creds)
            self.lbl_status.setText("Credentials: " + str(len(self._all_creds)))
        except Exception as e:
            self.lbl_status.setText("Error: " + str(e)[:100])
            self._all_creds = []
            self.table.setRowCount(0)

    def _populate_table(self, data):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", row.get("client_id", "-")))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("type", "-"))))
            code = str(row.get("code", row.get("qr_data", row.get("rfid_data", "-"))))
            self.table.setItem(i, 3, QTableWidgetItem(code[:20]))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("status", "-"))))
            self.table.setItem(i, 5, QTableWidgetItem(str(row.get("created_at", "-"))[:16]))

    def _filter(self, text):
        text = text.lower()
        if not text: self._populate_table(self._all_creds); return
        filtered = [r for r in self._all_creds if isinstance(r, dict) and (text in str(r.get("client_name", r.get("client_id", ""))).lower() or text in str(r.get("code", "")).lower())]
        self._populate_table(filtered)

    def _quick_check(self):
        code = self.txt_check.text().strip()
        if not code: return
        try:
            result = self.api.check_access({"credential": code, "location": "reception"})
            allowed = result.get("allowed", False)
            client = result.get("client_name", "Unknown")
            if allowed:
                self.lbl_result.setText("ACCESS GRANTED | " + client)
                self.lbl_result.setStyleSheet("color: #10b981; font-size: 16px; font-weight: bold; padding: 12px; background-color: #064e3b; border-radius: 8px; border: 1px solid #10b981;")
            else:
                self.lbl_result.setText("ACCESS DENIED | " + result.get("reason", "Access denied"))
                self.lbl_result.setStyleSheet("color: #f87171; font-size: 16px; font-weight: bold; padding: 12px; background-color: #450a0a; border-radius: 8px; border: 1px solid #f87171;")
        except Exception as e:
            self.lbl_result.setText("ERROR: " + str(e)[:100])
            self.lbl_result.setStyleSheet("color: #f87171; font-size: 16px; font-weight: bold; padding: 12px; background-color: #450a0a; border-radius: 8px; border: 1px solid #f87171;")

    def _gen_qr(self):
        client_id, ok = QInputDialog.getText(self, "Generate QR", "Enter client ID:")
        if ok and client_id:
            try:
                result = self.api._post("/credentials/qr", json_data={"client_id": client_id})
                QMessageBox.information(self, "Success", "QR: " + str(result.get("qr_data", "OK"))[:50])
                self.refresh()
            except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])

    def _gen_rfid(self):
        client_id, ok = QInputDialog.getText(self, "Generate RFID", "Enter client ID:")
        if ok and client_id:
            try:
                result = self.api._post("/credentials/rfid", json_data={"client_id": client_id})
                QMessageBox.information(self, "Success", "RFID: " + str(result.get("rfid_data", "OK"))[:50])
                self.refresh()
            except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])

    def _block(self):
        row = self.table.currentRow()
        if row < 0: QMessageBox.warning(self, "Error", "Select a credential first"); return
        cred_id = self.table.item(row, 0)
        if not cred_id: return
        try: self.api._post("/credentials/" + cred_id.text() + "/block"); QMessageBox.information(self, "Success", "Blocked"); self.refresh()
        except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])

    def _unblock(self):
        row = self.table.currentRow()
        if row < 0: QMessageBox.warning(self, "Error", "Select a credential first"); return
        cred_id = self.table.item(row, 0)
        if not cred_id: return
        try: self.api._post("/credentials/" + cred_id.text() + "/unblock"); QMessageBox.information(self, "Success", "Unblocked"); self.refresh()
        except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])
