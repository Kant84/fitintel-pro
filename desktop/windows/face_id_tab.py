"""Face ID Tab"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QInputDialog
from PyQt6.QtCore import Qt
from api.client import ApiClient
import random


class FaceIDTab(QWidget):
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
        title = QLabel("Face ID Control")
        title.setStyleSheet("color: #e2e8f0; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        btn_verify = QPushButton("Verify Face")
        btn_verify.setStyleSheet("QPushButton { background-color: #10b981; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #34d399; }")
        btn_verify.clicked.connect(self._verify)
        actions.addWidget(btn_verify)
        btn_register = QPushButton("Register Face")
        btn_register.setStyleSheet("QPushButton { background-color: #38bdf8; color: #0f172a; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #7dd3fc; }")
        btn_register.clicked.connect(self._register)
        actions.addWidget(btn_register)
        actions.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("QPushButton { background-color: #475569; color: #e2e8f0; border: none; border-radius: 6px; padding: 8px 16px; } QPushButton:hover { background-color: #64748b; }")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)
        settings = QHBoxLayout()
        settings.setSpacing(12)
        lbl_thresh = QLabel("Threshold:")
        lbl_thresh.setStyleSheet("color: #94a3b8; font-size: 13px;")
        settings.addWidget(lbl_thresh)
        self.cmb_threshold = QComboBox()
        self.cmb_threshold.addItems(["0.6 (Strict)", "0.5 (Normal)", "0.4 (Loose)"])
        self.cmb_threshold.setStyleSheet("QComboBox { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 6px; color: #e2e8f0; }")
        settings.addWidget(self.cmb_threshold)
        lbl_term = QLabel("Terminal:")
        lbl_term.setStyleSheet("color: #94a3b8; font-size: 13px;")
        settings.addWidget(lbl_term)
        self.txt_terminal = QLineEdit("desktop-001")
        self.txt_terminal.setStyleSheet("QLineEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; padding: 6px; color: #e2e8f0; }")
        settings.addWidget(self.txt_terminal)
        settings.addStretch()
        layout.addLayout(settings)
        self.lbl_result = QLabel("Ready")
        self.lbl_result.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold; padding: 16px; background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_result)
        sec = QLabel("Recognition Logs")
        sec.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: bold;")
        layout.addWidget(sec)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Time", "Client", "Action", "Confidence", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; gridline-color: #334155; } QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 8px; border: none; font-weight: bold; } QTableWidget::item { padding: 6px; } QTableWidget::item:selected { background-color: #38bdf8; color: #0f172a; }")
        layout.addWidget(self.table)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def refresh(self):
        try:
            logs = self.api.get_face_logs()
            if isinstance(logs, list):
                self.table.setRowCount(len(logs))
                for i, row in enumerate(logs):
                    if not isinstance(row, dict): continue
                    self.table.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", "-"))[:16]))
                    self.table.setItem(i, 1, QTableWidgetItem(str(row.get("client_name", row.get("client_id", "-")))))
                    self.table.setItem(i, 2, QTableWidgetItem(str(row.get("action", "-"))))
                    self.table.setItem(i, 3, QTableWidgetItem(str(row.get("confidence", "-"))))
                    self.table.setItem(i, 4, QTableWidgetItem(str(row.get("status", "-"))))
            else: self.table.setRowCount(0)
        except Exception as e: self.lbl_status.setText("Logs error: " + str(e)[:80])

    def _verify(self):
        try:
            face_encoding = [random.random() for _ in range(128)]
            terminal_id = self.txt_terminal.text().strip() or "desktop-001"
            result = self.api.verify_face(face_encoding, terminal_id)
            success = result.get("success", False)
            client = result.get("client_name", "Unknown")
            if success:
                self.lbl_result.setText("ACCESS GRANTED | Client: " + client)
                self.lbl_result.setStyleSheet("color: #10b981; font-size: 16px; font-weight: bold; padding: 16px; background-color: #064e3b; border-radius: 8px; border: 1px solid #10b981;")
            else:
                self.lbl_result.setText("ACCESS DENIED | " + result.get("reason", "Face not recognized"))
                self.lbl_result.setStyleSheet("color: #f87171; font-size: 16px; font-weight: bold; padding: 16px; background-color: #450a0a; border-radius: 8px; border: 1px solid #f87171;")
            self.refresh()
        except Exception as e:
            self.lbl_result.setText("ERROR: " + str(e)[:100])
            self.lbl_result.setStyleSheet("color: #f87171; font-size: 16px; font-weight: bold; padding: 16px; background-color: #450a0a; border-radius: 8px; border: 1px solid #f87171;")

    def _register(self):
        client_id, ok = QInputDialog.getText(self, "Register Face", "Enter client ID:")
        if ok and client_id:
            try:
                face_encoding = [random.random() for _ in range(128)]
                result = self.api.register_face({"client_id": client_id, "face_encoding": face_encoding, "terminal_id": self.txt_terminal.text().strip() or "desktop-001"})
                QMessageBox.information(self, "Success", "Face registered for: " + str(result.get("client_name", client_id)))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e)[:200])
