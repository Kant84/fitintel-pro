"""FitIntel Pro — Settings Tab (внешний вид, подключение, о программе)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

import os

from api import ApiClient
from windows import theme


class SettingsTab(QWidget):
    def __init__(self, api: ApiClient, main_window=None):
        super().__init__()
        self.api = api
        self.mw = main_window
        self._build_ui()
        self._sync_from_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Внешний вид ──
        box = QGroupBox("Внешний вид")
        form = QFormLayout(box)
        form.setSpacing(12)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("Светлая", "light")
        self.cmb_theme.addItem("Тёмная", "dark")
        self.cmb_theme.setStyleSheet("padding: 8px; min-width: 200px;")
        self.cmb_theme.currentIndexChanged.connect(self._theme_changed)
        form.addRow("Тема оформления:", self.cmb_theme)

        row_font = QHBoxLayout()
        b_minus = QPushButton("А−")
        b_minus.setFixedSize(48, 36)
        b_minus.setStyleSheet("font-weight: 700;")
        b_minus.clicked.connect(self._font_down)
        self.lbl_font = QLabel("10 pt")
        self.lbl_font.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_font.setMinimumWidth(70)
        b_plus = QPushButton("А+")
        b_plus.setFixedSize(48, 36)
        b_plus.setStyleSheet("font-weight: 700;")
        b_plus.clicked.connect(self._font_up)
        row_font.addWidget(b_minus)
        row_font.addWidget(self.lbl_font)
        row_font.addWidget(b_plus)
        row_font.addStretch()
        form.addRow("Размер шрифта:", row_font)

        hint = QLabel("Горячие клавиши: Ctrl++ / Ctrl− — масштаб; меню «Вид» — тема")
        hint.setStyleSheet("color: #64748b; font-size: 12px;")
        form.addRow(hint)
        layout.addWidget(box)

        # ── Подключение ──
        box2 = QGroupBox("Подключение")
        form2 = QFormLayout(box2)
        self.lbl_server = QLabel(self.api.base_url)
        form2.addRow("Сервер API:", self.lbl_server)
        b_check = QPushButton("Проверить связь")
        b_check.setStyleSheet("padding: 8px 16px; font-weight: 600;")
        b_check.clicked.connect(self._check)
        self.lbl_health = QLabel("—")
        form2.addRow(b_check, self.lbl_health)
        layout.addWidget(box2)

        # ── О программе ──
        box3 = QGroupBox("О программе")
        fl3 = QFormLayout(box3)
        fl3.addRow("Версия:", QLabel("FitIntel Pro Desktop v1.3.1"))
        fl3.addRow("Платформа:", QLabel("PyQt6 thin client"))
        layout.addWidget(box3)

        # ── Логи ──
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

        layout.addStretch()

    def _sync_from_settings(self):
        if not self.mw:
            return
        st = self.mw.ui_settings
        idx = 0 if st.get("theme") == "light" else 1
        self.cmb_theme.blockSignals(True)
        self.cmb_theme.setCurrentIndex(idx)
        self.cmb_theme.blockSignals(False)
        self.lbl_font.setText(f"{st.get('font_size', 10)} pt")

    def _theme_changed(self):
        if self.mw:
            self.mw.apply_appearance(theme=self.cmb_theme.currentData())
            self._sync_from_settings()

    def _font_up(self):
        if self.mw:
            self.mw.zoom_in()
            self._sync_from_settings()

    def _font_down(self):
        if self.mw:
            self.mw.zoom_out()
            self._sync_from_settings()

    def _check(self):
        try:
            h = self.api.health()
            self.lbl_health.setText("OK — сервер отвечает")
            self.lbl_health.setStyleSheet("color: #059669; font-weight: 600;")
        except Exception as e:
            self.lbl_health.setText(f"Ошибка: {e}")
            self.lbl_health.setStyleSheet("color: #ef4444; font-weight: 600;")


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
            self.lbl_tail.setText("\n".join(bad[-10:]) or "Ошибок нет")
        except Exception as e:
            self.lbl_tail.setText(f"Лог пуст: {e}")
