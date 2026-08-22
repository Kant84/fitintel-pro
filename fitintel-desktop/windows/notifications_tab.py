# -*- coding: utf-8 -*-
"""E58: вкладка «Оповещения» — настройки отправки уведомлений и шаблоны."""
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QSpinBox, QLineEdit, QPlainTextEdit, QScrollArea)
from . import theme

def _t(name, *args):
    f = getattr(theme, name, None)
    if not callable(f):
        return ""
    for a in (args, ()):
        try:
            return f(*a)
        except TypeError:
            continue
        except Exception:
            return ""
    return ""

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))

class NotificationsTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self.setStyleSheet(_t("widget_style"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        v = QVBoxLayout(inner)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        v.addWidget(QLabel("<b>Общие</b>"))
        self.chk_enabled = QCheckBox("Оповещения включены")
        self.chk_max = QCheckBox("Канал: мессенджер MAX")
        self.chk_dispatch = QCheckBox("Отправлять сразу после генерации")
        v.addWidget(self.chk_enabled)
        v.addWidget(self.chk_max)
        v.addWidget(self.chk_dispatch)
        row = QHBoxLayout()
        row.addWidget(QLabel("Время ежедневной отправки:"))
        self.ed_time = QLineEdit("10:00")
        self.ed_time.setMaximumWidth(80)
        row.addWidget(self.ed_time)
        row.addStretch(1)
        v.addLayout(row)

        v.addWidget(QLabel("<b>Напоминание: абонемент истекает</b>"))
        self.chk_expiry = QCheckBox("Включено")
        v.addWidget(self.chk_expiry)
        row = QHBoxLayout()
        row.addWidget(QLabel("За сколько дней напоминать:"))
        self.sp_expiry = QSpinBox()
        self.sp_expiry.setRange(1, 30)
        row.addWidget(self.sp_expiry)
        row.addStretch(1)
        v.addLayout(row)
        self.tpl_expiry = QPlainTextEdit()
        self.tpl_expiry.setMaximumHeight(60)
        self.tpl_expiry.setPlaceholderText("Переменные: {days} {date}")
        v.addWidget(self.tpl_expiry)

        v.addWidget(QLabel("<b>Напоминание: клиент пропал</b>"))
        self.chk_inactive = QCheckBox("Включено")
        v.addWidget(self.chk_inactive)
        row = QHBoxLayout()
        row.addWidget(QLabel("Не приходил, дней:"))
        self.sp_inactive = QSpinBox()
        self.sp_inactive.setRange(3, 365)
        row.addWidget(self.sp_inactive)
        row.addStretch(1)
        v.addLayout(row)
        self.tpl_inactive = QPlainTextEdit()
        self.tpl_inactive.setMaximumHeight(60)
        self.tpl_inactive.setPlaceholderText("Переменные: {days}")
        v.addWidget(self.tpl_inactive)

        v.addWidget(QLabel("<b>Поздравление с днём рождения</b>"))
        self.chk_bday = QCheckBox("Включено")
        v.addWidget(self.chk_bday)
        self.tpl_bday = QPlainTextEdit()
        self.tpl_bday.setMaximumHeight(60)
        v.addWidget(self.tpl_bday)

        bar = QHBoxLayout()
        b1 = QPushButton("💾 Сохранить настройки")
        b1.clicked.connect(self.save)
        b2 = QPushButton("🔔 Сгенерировать и отправить сейчас")
        b2.clicked.connect(self.run_now)
        bar.addWidget(b1)
        bar.addWidget(b2)
        bar.addStretch(1)
        v.addLayout(bar)
        v.addStretch(1)

        scroll.setWidget(inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        self.load()

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda m: self._show(m, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    def load(self):
        self._run(self.api.get_notif_settings, self._fill)

    def _fill(self, cfg):
        if not isinstance(cfg, dict):
            return
        self.chk_enabled.setChecked(bool(cfg.get("enabled", True)))
        self.chk_max.setChecked(bool(cfg.get("channel_max", True)))
        self.chk_dispatch.setChecked(bool(cfg.get("auto_dispatch", True)))
        self.ed_time.setText(str(cfg.get("send_time", "10:00")))
        self.chk_expiry.setChecked(bool(cfg.get("expiry_enabled", True)))
        self.sp_expiry.setValue(int(cfg.get("expiry_days", 3)))
        self.tpl_expiry.setPlainText(str(cfg.get("expiry_template", "")))
        self.chk_inactive.setChecked(bool(cfg.get("inactive_enabled", True)))
        self.sp_inactive.setValue(int(cfg.get("inactive_days", 14)))
        self.tpl_inactive.setPlainText(str(cfg.get("inactive_template", "")))
        self.chk_bday.setChecked(bool(cfg.get("birthday_enabled", False)))
        self.tpl_bday.setPlainText(str(cfg.get("birthday_template", "")))
        self._show("Настройки загружены.")

    def save(self):
        cfg = {
            "enabled": self.chk_enabled.isChecked(),
            "channel_max": self.chk_max.isChecked(),
            "auto_dispatch": self.chk_dispatch.isChecked(),
            "send_time": self.ed_time.text().strip() or "10:00",
            "expiry_enabled": self.chk_expiry.isChecked(),
            "expiry_days": self.sp_expiry.value(),
            "expiry_template": self.tpl_expiry.toPlainText(),
            "inactive_enabled": self.chk_inactive.isChecked(),
            "inactive_days": self.sp_inactive.value(),
            "inactive_template": self.tpl_inactive.toPlainText(),
            "birthday_enabled": self.chk_bday.isChecked(),
            "birthday_template": self.tpl_bday.toPlainText(),
        }
        self._run(lambda: self.api.save_notif_settings(cfg),
                  lambda _r: self._show("Настройки сохранены."))

    def run_now(self):
        def _done(r):
            if isinstance(r, dict):
                self._show("Создано: %s, отправлено: %s, ошибок: %s. %s"
                           % (r.get("created"), r.get("sent", "-"),
                              r.get("failed", "-"),
                              "; ".join(r.get("notes") or [])))
        self._run(self.api.run_reminders, _done)
