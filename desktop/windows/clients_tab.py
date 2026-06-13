"""Clients Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout, QComboBox, QTextEdit
from PyQt6.QtCore import Qt
from api.client import ApiClient


class ClientEditDialog(QDialog):
    def __init__(self, api, client=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Client" if client else "Add Client")
        self.setMinimumWidth(500)
        self.setStyleSheet("QDialog { background-color: #1e293b; } QLabel { color: #e2e8f0; font-size: 13px; } QLineEdit, QTextEdit, QComboBox { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus, QTextEdit:focus { border-color: #38bdf8; } QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; } QPushButton#cancel { background-color: transparent; color: #94a3b8; border: 1px solid #475569; } QPushButton#cancel:hover { background-color: #334155; }")
        self._build_ui(client or {})

    def _build_ui(self, client):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        form = QFormLayout()
        form.setSpacing(12)
        self.txt_name = QLineEdit()
        self.txt_name.setText(client.get("name", ""))
        form.addRow("Full Name *", self.txt_name)
        self.txt_phone = QLineEdit()
        self.txt_phone.setText(client.get("phone", ""))
        form.addRow("Phone", self.txt_phone)
        self.txt_email = QLineEdit()
        self.txt_email.setText(client.get("email", ""))
        form.addRow("Email", self.txt_email)
        self.txt_card = QLineEdit()
        self.txt_card.setText(client.get("card_number", ""))
        form.addRow("Card Number", self.txt_card)
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["", "Male", "Female"])
        form.addRow("Gender", self.cmb_gender)
        self.txt_birth = QLineEdit()
        self.txt_birth.setText(client.get("birth_date", ""))
        self.txt_birth.setPlaceholderText("YYYY-MM-DD")
        form.addRow("Birth Date", self.txt_birth)
        self.txt_notes = QTextEdit()
        self.txt_notes.setText(client.get("notes", ""))
        self.txt_notes.setMaximumHeight(80)
        form.addRow("Notes", self.txt_notes)
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
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name is required")
            return
        self.data = {"name": name, "phone": self.txt_phone.text().strip(), "email": self.txt_email.text().strip(), "card_number": self.txt_card.text().strip(), "gender": self.cmb_gender.currentText(), "birth_date": self.txt_birth.text().strip(), "notes": self.txt_notes.toPlainText().strip()}
        self.accept()

    def get_data(self):
        return getattr(self, "data", {})


class ClientsTab(QWidget):
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
        title = QLabel("Clients")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by name, phone, card...")
        self.txt_search.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; font-size: 13px; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_search.textChanged.connect(self._filter)
        toolbar.addWidget(self.txt_search)
        toolbar.addStretch()
        btn_add = QPushButton("+ Add Client")
        btn_add.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #34d399; }")
        btn_add.clicked.connect(self._add_client)
        toolbar.addWidget(btn_add)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Card", "Gender", "Status", "Birth Date", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 80)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.lbl_status = QLabel("Loading...")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            data = self.api.get_clients()
            if isinstance(data, list): self._all_data = data
            elif isinstance(data, dict) and "items" in data: self._all_data = data["items"]
            else: self._all_data = []
            self._populate_table(self._all_data)
            self.lbl_status.setText("Total clients: " + str(len(self._all_data)))
        except Exception as e:
            self.lbl_status.setText("Error: " + str(e)[:100])

    def _populate_table(self, data):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("name", "-"))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("phone", "-"))))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("card_number", "-"))))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("gender", "-"))))
            self.table.setItem(i, 5, QTableWidgetItem(str(row.get("status", "active"))))
            self.table.setItem(i, 6, QTableWidgetItem(str(row.get("birth_date", "-"))))
            self.table.setItem(i, 7, QTableWidgetItem("Edit"))

    def _filter(self, text):
        text = text.lower()
        if not text: self._populate_table(self._all_data); return
        filtered = [r for r in self._all_data if isinstance(r, dict) and (text in str(r.get("name", "")).lower() or text in str(r.get("phone", "")).lower() or text in str(r.get("card_number", "")).lower() or text in str(r.get("email", "")).lower())]
        self._populate_table(filtered)

    def _add_client(self):
        dlg = ClientEditDialog(self.api, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_client(dlg.get_data())
                QMessageBox.information(self, "Success", "Client created")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e)[:200])
