import io

p = "windows/settings_tab.py"
src = io.open(p, encoding="utf-8").read()

src = src.replace(
    "from api import ApiClient",
    "import os\n\nfrom api import ApiClient")

src = src.replace(
    "        layout.addStretch()",
    '''        # ── Логи ──
        box4 = QGroupBox("Логи")
        fl4 = QFormLayout(box4)
        try:
            from app_logging import LOG_FILE, LOG_DIR
            self.lbl_log = QLabel(str(LOG_FILE))
        except Exception:
            from pathlib import Path
            self.lbl_log = QLabel(str(Path("logs") / "client.log"))
        self.lbl_log.setStyleSheet("font-size: 11px;")
        self.lbl_log.setWordWrap(True)
        fl4.addRow("Файл лога:", self.lbl_log)
        row_log = QHBoxLayout()
        b_open = QPushButton("Открыть папку логов")
        b_open.setStyleSheet("padding: 8px 16px; font-weight: 600;")
        b_open.clicked.connect(self._open_logs)
        row_log.addWidget(b_open)
        b_tail = QPushButton("Показать последние ошибки")
        b_tail.setStyleSheet("padding: 8px 16px; font-weight: 600;")
        b_tail.clicked.connect(self._show_tail)
        row_log.addWidget(b_tail)
        row_log.addStretch()
        fl4.addRow(row_log)
        self.lbl_tail = QLabel("")
        self.lbl_tail.setWordWrap(True)
        self.lbl_tail.setStyleSheet("font-size: 11px; color: #b91c1c;")
        fl4.addRow(self.lbl_tail)
        layout.addWidget(box4)

        layout.addStretch()''')

src += '''

    def _open_logs(self):
        try:
            from app_logging import LOG_DIR
            os.startfile(str(LOG_DIR))
        except Exception:
            pass

    def _show_tail(self):
        try:
            from app_logging import LOG_FILE
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
            bad = [l for l in lines if "WARNING" in l or "ERROR" in l or "CRITICAL" in l]
            self.lbl_tail.setText("\\n".join(bad[-10:]) or "Ошибок нет")
        except Exception as e:
            self.lbl_tail.setText(f"Лог пуст: {e}")
'''
io.open(p, "w", encoding="utf-8").write(src)
print("settings_tab PATCHED")
