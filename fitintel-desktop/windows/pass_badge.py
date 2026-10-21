# -*- coding: utf-8 -*-
"""W22: мини-индикатор прохода — ФИО + цветной кружок. Не мешает: полупрозрачный,
в углу, без рамки, автоскрытие 6 сек. Переключатель: меню Вид / pass_badge_enabled."""
import json, os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QFont

SETTINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "client_settings.json")


def load_enabled():
    try:
        return bool(json.load(open(SETTINGS, encoding="utf-8")).get("pass_badge_enabled", True))
    except Exception:
        return True


def save_enabled(v):
    try:
        cfg = json.load(open(SETTINGS, encoding="utf-8"))
        cfg["pass_badge_enabled"] = bool(v)
        json.dump(cfg, open(SETTINGS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


class PassBadge(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(250, 54)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        self.dot = QLabel("\u25cf")
        self.dot.setFont(QFont("Segoe UI", 20))
        self.dot.setStyleSheet("color: #64748b;")
        lay.addWidget(self.dot)
        v = QVBoxLayout()
        v.setSpacing(0)
        self.name = QLabel("\u2014")
        self.name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.name.setStyleSheet("color: #e2e8f0;")
        self.sub = QLabel("")
        self.sub.setFont(QFont("Segoe UI", 9))
        self.sub.setStyleSheet("color: #94a3b8;")
        v.addWidget(self.name)
        v.addWidget(self.sub)
        lay.addLayout(v, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._anim = None

    def _pos(self):
        scr = self.screen().availableGeometry() if self.screen() else None
        if scr:
            self.move(scr.x() + scr.width() - self.width() - 12,
                      scr.y() + scr.height() - self.height() - 48)

    def show_result(self, fio, allow, note=""):
        if not load_enabled():
            self.hide()
            return
        self.name.setText((fio or "\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u044b\u0439")[:28])
        if allow is True:
            self.dot.setStyleSheet("color: #22c55e;")
            self.sub.setText("\u0432\u0445\u043e\u0434 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d" + (" \u00b7 " + note if note else ""))
        elif allow is False:
            self.dot.setStyleSheet("color: #ef4444;")
            self.sub.setText("\u043e\u0442\u043a\u0430\u0437" + (" \u00b7 " + note if note else ""))
        else:
            self.dot.setStyleSheet("color: #64748b;")
            self.sub.setText("\u043d\u0435\u0442 \u0441\u0432\u044f\u0437\u0438")
        self.setWindowOpacity(0.55)
        self._pos()
        self.show()
        self._timer.start(6000)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(400)
        anim.setStartValue(0.55)
        anim.setEndValue(0.85)
        anim.start()
        self._anim = anim

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(500)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim = anim

def load_scan_visit():
    try:
        return bool(json.load(open(SETTINGS, encoding="utf-8")).get("scan_makes_visit", False))
    except Exception:
        return False


def save_scan_visit(v):
    try:
        cfg = json.load(open(SETTINGS, encoding="utf-8"))
        cfg["scan_makes_visit"] = bool(v)
        json.dump(cfg, open(SETTINGS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass
