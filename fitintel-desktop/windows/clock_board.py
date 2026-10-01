# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Табло с часами — компактная плашка вверху по центру экрана.
Поверх окон, не перехватывает фокус, не мешает работе. Esc или ✕ — закрыть."""
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer, Qt, QDateTime
from PyQt6.QtGui import QFont, QGuiApplication


class ClockBoardDialog(QDialog):
    def __init__(self, parent=None, club_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("FitIntel Pro — Часы")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFixedSize(250, 60)
        self.setStyleSheet(
            "QDialog { background: #0f172a; border: 1px solid #334155; "
            "border-radius: 10px; }")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 8, 6)

        self.lbl_time = QLabel("--:--:--")
        self.lbl_time.setFont(QFont("Consolas", 22, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet("color: #00f0ff; background: transparent;")
        lay.addWidget(self.lbl_time)

        lay.addStretch(1)

        self.lbl_date = QLabel("")
        self.lbl_date.setFont(QFont("Segoe UI", 9))
        self.lbl_date.setStyleSheet("color: #64748b; background: transparent;")
        lay.addWidget(self.lbl_date)

        b = QPushButton("✕")
        b.setFixedSize(22, 22)
        b.setStyleSheet(
            "QPushButton { background: transparent; color: #64748b; "
            "border: none; border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #334155; color: #f87171; }")
        b.setToolTip("Закрыть часы")
        b.clicked.connect(self.close)
        lay.addWidget(b)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

        # позиция: верхний центр основного экрана
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.x() + (screen.width() - self.width()) // 2,
                  screen.y() + 12)

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.lbl_time.setText(now.toString("HH:mm:ss"))
        self.lbl_date.setText(now.toString("dd.MM.yyyy"))

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(ev)