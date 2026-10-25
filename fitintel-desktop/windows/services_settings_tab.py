"""W5: подвкладка «Сервисы» — настройка сторонних сервисов НА СЕРВЕРЕ из десктопа
(без ssh/.env): MAX, ЮKassa, SMS, Telegram, СКУД ITC, СБП. Банки вынесены в отдельный экран.
Хранение: server_settings (талица БД). Секреты показываются маской."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLineEdit,
    QPushButton, QLabel, QMessageBox, QScrollArea, QComboBox, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal

from api import ApiClient
from windows import theme


class _Get(QThread):
    done = pyqtSignal(list)
    fail = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            r = self.api.session.get(self.api._url("/server-settings"), timeout=20)
            r.raise_for_status()
            self.done.emit(r.json())
        except Exception as e:
            self.fail.emit(str(e))


class ServicesSettingsTab(QWidget):
    GROUPS = {
        "MAX-бот": ["MAX_BOT_TOKEN", "MAX_BOT_WEBHOOK_SECRET"],
        "ЮKassa (онлайн-оплата)": ["YOOKASSA_ACCOUNT_ID", "YOOKASSA_SECRET_KEY",
                                   "YOOKASSA_WEBHOOK_SECRET", "YOOKASSA_TEST_MODE"],
        "SMS (smsc.ru)": ["SMS_USER", "SMS_PASSWORD"],
        "Telegram": ["TELEGRAM_BOT_TOKEN"],
        "СКУД ITC": ["ITC_BASIC_USER", "ITC_BASIC_PASSWORD"],
        "СБП": ["SBP_MOCK"],
    }

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._edits = {}
        self._meta = {}
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self.lay = QVBoxLayout(host)
        self.lay.setSpacing(10)
        scroll.setWidget(host)
        root.addWidget(scroll)

        bar = QHBoxLayout()
        b = QPushButton("Сохранить всё")
        b.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600; }")
        b.clicked.connect(self._save_all)
        bar.addWidget(b)
        b2 = QPushButton("Обновить")
        b2.clicked.connect(self.refresh)
        bar.addWidget(b2)
        bar.addStretch()
        hint = QLabel("Настройки пишутся на сервер (таблица server_settings) и действуют без перезапуска. "
                      "Секреты отображаются маской.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b; font-size: 12px;")
        bar.addWidget(hint, 1)
        root.addLayout(bar)
        self.refresh()

    def refresh(self):
        for grp in self.lay.findChildren(QGroupBox):
            grp.deleteLater()
        self._edits = {}
        self._get = _Get(self.api)
        self._get.done.connect(self._build)
        self._get.fail.connect(lambda m: QMessageBox.warning(self, "Сервисы", m))
        self._get.start()

    def _build(self, rows: list):
        for r in rows:
            self._meta[r["key"]] = r
        for title, keys in self.GROUPS.items():
            gb = QGroupBox(title)
            form = QFormLayout(gb)
            for k in keys:
                meta = self._meta.get(k, {"description": k, "is_set": False})
                ed = QLineEdit()
                ed.setPlaceholderText(meta.get("description", k))
                if k == "SBP_MOCK" or k == "YOOKASSA_TEST_MODE":
                    ed.setText(str(meta.get("value") or ("true" if k == "SBP_MOCK" else "false")))
                elif meta.get("is_set") and meta.get("value") and "•" in str(meta.get("value")):
                    ed.setPlaceholderText(str(meta["value"]) + "  (задано — ввод заменит)")
                elif meta.get("value"):
                    ed.setText(str(meta["value"]))
                ed.setStyleSheet("padding: 6px;")
                self._edits[k] = ed
                form.addRow(f"{k}:", ed)
            self.lay.addWidget(gb)
        self.lay.addStretch()

    def _save_all(self):
        saved, failed = 0, []
        for k, ed in self._edits.items():
            v = ed.text().strip()
            if not v:
                continue
            try:
                r = self.api.session.put(self.api._url("/server-settings"),
                                         json={"key": k, "value": v}, timeout=15)
                if r.status_code == 200:
                    saved += 1
                else:
                    failed.append(f"{k}: {r.status_code}")
            except Exception as e:
                failed.append(f"{k}: {str(e)[:60]}")
        msg = f"Сохранено: {saved}"
        if failed:
            msg += "\nОшибки: " + "; ".join(failed[:4])
        QMessageBox.information(self, "Сервисы", msg)
        self.refresh()