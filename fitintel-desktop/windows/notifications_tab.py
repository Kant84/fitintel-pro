# -*- coding: utf-8 -*-
"""E17 v2: Уведомления — подвкладки Email/SMS/WebPush/Тест/Журнал + контакты из базы."""
import json, os
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QGroupBox, QSpinBox, QTabWidget, QLabel)


def _base():
    try:
        cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "client_settings.json"), encoding="utf-8"))
        return cfg.get("base_url") or cfg.get("base") or "http://localhost:8001/api/v1"
    except Exception:
        return "http://localhost:8001/api/v1"


class NotificationsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        lay.addWidget(self.tabs)

        self._build_email_tab()
        self._build_sms_tab()
        self._build_push_tab()
        self._build_test_tab()
        self._build_log_tab()

        self.load_settings()
        self.load_log()
        self.load_contacts()

    # ---------- подвкладки ----------
    def _build_email_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.cb_email = QCheckBox("Включить Email-уведомления")
        f.addRow(self.cb_email)
        self.ed_smtp_host = QLineEdit(); self.ed_smtp_host.setPlaceholderText("smtp.yandex.ru")
        self.ed_smtp_port = QSpinBox(); self.ed_smtp_port.setRange(1, 65535); self.ed_smtp_port.setValue(465)
        self.ed_smtp_user = QLineEdit()
        self.ed_smtp_pass = QLineEdit(); self.ed_smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_from = QLineEdit()
        self.ed_digest = QLineEdit("09:00"); self.ed_digest.setMaximumWidth(90)
        f.addRow("SMTP хост:", self.ed_smtp_host)
        f.addRow("SMTP порт (465=SSL, 587=TLS):", self.ed_smtp_port)
        f.addRow("SMTP логин:", self.ed_smtp_user)
        f.addRow("SMTP пароль:", self.ed_smtp_pass)
        f.addRow("От кого (email):", self.ed_from)
        f.addRow("Время ежедневного дайджеста:", self.ed_digest)
        b = QPushButton("💾 Сохранить Email"); b.clicked.connect(lambda: self.save_settings("email"))
        f.addRow(b)
        self.tabs.addTab(w, "📧 Email")

    def _build_sms_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.cb_sms = QCheckBox("Включить SMS (smsc.ru)")
        f.addRow(self.cb_sms)
        self.ed_smsc_login = QLineEdit()
        self.ed_smsc_pass = QLineEdit(); self.ed_smsc_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_smsc_sender = QLineEdit(); self.ed_smsc_sender.setPlaceholderText("FitIntel")
        f.addRow("SMSC логин:", self.ed_smsc_login)
        f.addRow("SMSC пароль:", self.ed_smsc_pass)
        f.addRow("Подпись отправителя:", self.ed_smsc_sender)
        b = QPushButton("💾 Сохранить SMS"); b.clicked.connect(lambda: self.save_settings("sms"))
        f.addRow(b)
        self.tabs.addTab(w, "📱 SMS")

    def _build_push_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.cb_push = QCheckBox("Включить Web Push")
        f.addRow(self.cb_push)
        f.addRow(QLabel("VAPID-ключи генерируются один раз: pywebpush (vp --gen)."))
        self.ed_vapid_pub = QLineEdit()
        self.ed_vapid_priv = QLineEdit(); self.ed_vapid_priv.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_vapid_sub = QLineEdit(); self.ed_vapid_sub.setPlaceholderText("mailto:admin@club.ru")
        f.addRow("VAPID public:", self.ed_vapid_pub)
        f.addRow("VAPID private:", self.ed_vapid_priv)
        f.addRow("VAPID sub:", self.ed_vapid_sub)
        b = QPushButton("💾 Сохранить Web Push"); b.clicked.connect(lambda: self.save_settings("push"))
        f.addRow(b)
        self.tabs.addTab(w, "🔔 Web Push")

    def _build_test_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.cmb_ch = QComboBox(); self.cmb_ch.addItems(["email", "sms", "webpush"])
        f.addRow("Канал:", self.cmb_ch)
        hb = QHBoxLayout()
        self.cmb_contacts = QComboBox(); self.cmb_contacts.setEditable(True)
        self.cmb_contacts.setPlaceholderText("Контакты из базы клиентов…")
        btn_rc = QPushButton("🔄"); btn_rc.setMaximumWidth(40); btn_rc.clicked.connect(self.load_contacts)
        hb.addWidget(self.cmb_contacts); hb.addWidget(btn_rc)
        f.addRow("Получатель из базы:", hb)
        self.ed_to = QLineEdit(); self.ed_to.setPlaceholderText("или вручную: email / +7...")
        f.addRow("Получатель вручную:", self.ed_to)
        self.cmb_contacts.currentIndexChanged.connect(self._contact_picked)
        self.ed_msg = QLineEdit("Тестовое уведомление FitIntel Pro")
        f.addRow("Текст:", self.ed_msg)
        hb2 = QHBoxLayout()
        bt = QPushButton("📨 Отправить тест"); bt.clicked.connect(self.send_test)
        bd = QPushButton("📊 Отправить дайджест"); bd.clicked.connect(self.send_digest)
        hb2.addWidget(bt); hb2.addWidget(bd)
        f.addRow(hb2)
        self.tabs.addTab(w, "📨 Тест")

    def _build_log_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        b = QPushButton("🔄 Обновить журнал"); b.clicked.connect(self.load_log)
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["ID", "Канал", "Кому", "Тема", "Статус", "Ошибка"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        v.addWidget(b); v.addWidget(self.tbl)
        self.tabs.addTab(w, "📋 Журнал")

    # ---------- логика ----------
    def _get(self, path):
        return requests.get(_base() + path, timeout=15).json()

    def _post(self, path, payload):
        return requests.post(_base() + path, json=payload, timeout=25).json()

    def load_contacts(self):
        try:
            rows = self._get("/notify/contacts")
            self.cmb_contacts.clear()
            self._contacts = []
            if isinstance(rows, list):
                for r in rows:
                    for kind in ("email", "phone"):
                        val = (r.get(kind) or "").strip()
                        if val:
                            label = f"{r.get('name') or '?'} — {val}"
                            self.cmb_contacts.addItem(label, val)
                            self._contacts.append(val)
        except Exception as e:
            print("[E17] contacts:", e)

    def _contact_picked(self, idx):
        val = self.cmb_contacts.itemData(idx)
        if val:
            self.ed_to.setText(val)

    def load_settings(self):
        try:
            s = self._get("/notify/settings")
            self.cb_email.setChecked(bool(s.get("email_enabled")))
            self.cb_sms.setChecked(bool(s.get("sms_enabled")))
            self.cb_push.setChecked(bool(s.get("webpush_enabled")))
            self.ed_smtp_host.setText(s.get("smtp_host") or "")
            self.ed_smtp_port.setValue(int(s.get("smtp_port") or 465))
            self.ed_smtp_user.setText(s.get("smtp_user") or "")
            self.ed_smtp_pass.setText(s.get("smtp_pass") or "")
            self.ed_from.setText(s.get("email_from") or "")
            self.ed_smsc_login.setText(s.get("smsc_login") or "")
            self.ed_smsc_pass.setText(s.get("smsc_pass") or "")
            self.ed_smsc_sender.setText(s.get("smsc_sender") or "")
            self.ed_digest.setText(s.get("digest_time") or "09:00")
            self.ed_vapid_pub.setText(s.get("vapid_public") or "")
            self.ed_vapid_priv.setText(s.get("vapid_private") or "")
            self.ed_vapid_sub.setText(s.get("vapid_sub") or "")
        except Exception as e:
            print("[E17] settings load:", e)

    def save_settings(self, part):
        payload = {}
        if part == "email":
            payload = {"email_enabled": self.cb_email.isChecked(),
                       "smtp_host": self.ed_smtp_host.text().strip(),
                       "smtp_port": self.ed_smtp_port.value(),
                       "smtp_user": self.ed_smtp_user.text().strip(),
                       "smtp_pass": self.ed_smtp_pass.text(),
                       "email_from": self.ed_from.text().strip(),
                       "digest_time": self.ed_digest.text().strip() or "09:00"}
        elif part == "sms":
            payload = {"sms_enabled": self.cb_sms.isChecked(),
                       "smsc_login": self.ed_smsc_login.text().strip(),
                       "smsc_pass": self.ed_smsc_pass.text(),
                       "smsc_sender": self.ed_smsc_sender.text().strip()}
        elif part == "push":
            payload = {"webpush_enabled": self.cb_push.isChecked(),
                       "vapid_public": self.ed_vapid_pub.text().strip(),
                       "vapid_private": self.ed_vapid_priv.text().strip(),
                       "vapid_sub": self.ed_vapid_sub.text().strip()}
        try:
            r = self._post("/notify/settings", payload)
            QMessageBox.information(self, "Уведомления", "Сохранено ✓" if r.get("ok") else str(r))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def send_test(self):
        try:
            r = self._post("/notify/test", {"channel": self.cmb_ch.currentText(),
                "to": self.ed_to.text().strip(), "message": self.ed_msg.text()})
            QMessageBox.information(self, "Тест", "Отправлено ✓" if r.get("ok") else f"Ошибка: {r.get('error')}")
            self.load_log()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def send_digest(self):
        try:
            r = self._post("/notify/digest", {})
            st = r.get("stats") or {}
            QMessageBox.information(self, "Дайджест",
                ("Отправлен ✓" if r.get("ok") else f"Ошибка: {r.get('error')}") +
                f"\nКлиентов: {st.get('clients')}, посещений: {st.get('visits_today')}, выручка: {st.get('revenue_today')}")
            self.load_log()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_log(self):
        try:
            rows = self._get("/notify/log?limit=50")
            self.tbl.setRowCount(len(rows) if isinstance(rows, list) else 0)
            for i, r in enumerate(rows if isinstance(rows, list) else []):
                for j, k in enumerate(("id", "channel", "recipient", "subject", "status", "error")):
                    self.tbl.setItem(i, j, QTableWidgetItem(str(r.get(k) or "")))
        except Exception as e:
            print("[E17] log load:", e)
