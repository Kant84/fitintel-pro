"""Users & RBAC Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QDialog, QFormLayout
from PyQt6.QtCore import Qt
from api.client import ApiClient


class UserEditDialog(QDialog):
    def __init__(self, api, user, roles, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self.roles = roles or []
        self.setWindowTitle("Edit User" if user else "New User")
        self.setMinimumWidth(400)
        self.setStyleSheet("QDialog { background-color: #1e293b; } QLabel { color: #e2e8f0; font-size: 13px; } QLineEdit, QComboBox { background-color: #0f172a; border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e2e8f0; font-size: 13px; } QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; } QPushButton:hover { background-color: #7dd3fc; } QPushButton#cancel { background-color: transparent; color: #94a3b8; border: 1px solid #475569; } QPushButton#cancel:hover { background-color: #334155; }")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        form.setSpacing(10)
        self.txt_username = QLineEdit()
        self.txt_username.setText(self.user.get("username", ""))
        form.addRow("Username *", self.txt_username)
        self.txt_email = QLineEdit()
        self.txt_email.setText(self.user.get("email", ""))
        form.addRow("Email", self.txt_email)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Leave blank to keep current")
        form.addRow("Password", self.txt_password)
        self.cmb_role = QComboBox()
        for r in self.roles: self.cmb_role.addItem(str(r.get("name", "-")), r.get("id"))
        form.addRow("Role", self.cmb_role)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["active", "inactive"])
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
        username = self.txt_username.text().strip()
        if not username: QMessageBox.warning(self, "Error", "Username is required"); return
        self.data = {"username": username, "email": self.txt_email.text().strip(), "role_id": self.cmb_role.currentData(), "status": self.cmb_status.currentText()}
        pwd = self.txt_password.text().strip()
        if pwd: self.data["password"] = pwd
        self.accept()

    def get_data(self): return getattr(self, "data", {})


class UsersTab(QWidget):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self._all_users = []
        self._roles = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Users & RBAC")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search users...")
        self.txt_search.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; } QLineEdit:focus { border-color: #38bdf8; }")
        self.txt_search.textChanged.connect(self._filter)
        toolbar.addWidget(self.txt_search)
        toolbar.addStretch()
        btn_add = QPushButton("+ Add User")
        btn_add.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background-color: #34d399; }")
        btn_add.clicked.connect(self._add_user)
        toolbar.addWidget(btn_add)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)
        sec1 = QLabel("Users")
        sec1.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold;")
        layout.addWidget(sec1)
        self.table_users = QTableWidget()
        self.table_users.setColumnCount(6)
        self.table_users.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role", "Status", "Created"])
        self.table_users.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_users.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table_users)
        sec2 = QLabel("Roles")
        sec2.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(sec2)
        self.table_roles = QTableWidget()
        self.table_roles.setColumnCount(3)
        self.table_roles.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.table_roles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_roles.setMaximumHeight(150)
        self.table_roles.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table_roles)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            data = self.api.get_users()
            if isinstance(data, list): self._all_users = data
            elif isinstance(data, dict) and "items" in data: self._all_users = data["items"]
            else: self._all_users = []
            self._populate_users(self._all_users)
        except Exception as e: self.lbl_status.setText("Users error: " + str(e)[:80])
        try:
            self._roles = self.api.get_roles()
            if not isinstance(self._roles, list): self._roles = []
            self.table_roles.setRowCount(len(self._roles))
            for i, r in enumerate(self._roles):
                if not isinstance(r, dict): continue
                self.table_roles.setItem(i, 0, QTableWidgetItem(str(r.get("id", ""))[:8]))
                self.table_roles.setItem(i, 1, QTableWidgetItem(str(r.get("name", "-"))))
                self.table_roles.setItem(i, 2, QTableWidgetItem(str(r.get("description", "-"))))
        except: pass
        self.lbl_status.setText("Users: " + str(len(self._all_users)) + " | Roles: " + str(len(self._roles)))

    def _populate_users(self, data):
        self.table_users.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            self.table_users.setItem(i, 0, QTableWidgetItem(str(row.get("id", ""))[:8]))
            self.table_users.setItem(i, 1, QTableWidgetItem(str(row.get("username", "-"))))
            self.table_users.setItem(i, 2, QTableWidgetItem(str(row.get("email", "-"))))
            self.table_users.setItem(i, 3, QTableWidgetItem(str(row.get("role_name", row.get("role_id", "-")))))
            self.table_users.setItem(i, 4, QTableWidgetItem(str(row.get("status", "-"))))
            self.table_users.setItem(i, 5, QTableWidgetItem(str(row.get("created_at", "-"))[:16]))

    def _filter(self, text):
        text = text.lower()
        if not text: self._populate_users(self._all_users); return
        filtered = [r for r in self._all_users if isinstance(r, dict) and (text in str(r.get("username", "")).lower() or text in str(r.get("email", "")).lower())]
        self._populate_users(filtered)

    def _add_user(self):
        if not self._roles: QMessageBox.warning(self, "Warning", "No roles loaded. Refresh first."); return
        dlg = UserEditDialog(self.api, None, self._roles, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_user(dlg.get_data())
                QMessageBox.information(self, "Success", "User created")
                self.refresh()
            except Exception as e: QMessageBox.critical(self, "Error", str(e)[:200])
