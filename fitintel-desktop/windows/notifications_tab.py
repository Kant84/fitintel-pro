# -*- coding: utf-8 -*-
"""E17 v2: Уведомления — подвкладки Email/SMS/WebPush/Отправка/Журнал + контакты из базы."""
import json, os
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QGroupBox, QSpinBox, QTabWidget, QLabel)


def _base():
    try:
        cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "client_settings.json"), encoding="utf-8"))
        return cfg.get("api_base") or cfg.get("base_url") or cfg.get("base") or "http://localhost:8001/api/v1"
    except Exception:
        return "http://localhost:8001/api/v1"


# Русские статусы для журнала
STATUS_RU = {"sent": "Отправлено", "error": "Ошибка", "queued": "На отправлении",
             "failed": "Ошибка", "pending": "На отправлении"}


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
        self._build_client_tab()
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
        b = QPushButton(" Сохранить Email"); b.clicked.connect(lambda: self.save_settings("email"))
        f.addRow(b)
        self.tabs.addTab(w, " Email")

    def _build_client_tab(self):
        w = QWidget(); f = QFormLayout(w)
        self.cb_cn = QCheckBox("Включить уведомления клиентам (MAX → Telegram → SMS)")
        f.addRow(self.cb_cn)
        self.cb_cn_max = QCheckBox("MAX (мессенджер, бесплатно)")
        self.cb_cn_tg = QCheckBox("Telegram (бесплатно)")
        self.cb_cn_sms = QCheckBox("SMS через SMSC.ru (платно: ~5–11 ₽/шт)")
        f.addRow(self.cb_cn_max); f.addRow(self.cb_cn_tg); f.addRow(self.cb_cn_sms)
        f.addRow(QLabel("События:"))
        self.cb_ev_pay = QCheckBox("Оплата принята")
        self.cb_ev_vend = QCheckBox("Вендинг-покупка")
        self.cb_ev_book = QCheckBox("Напоминание о записи")
        self.cb_ev_exp = QCheckBox("Абонемент истекает")
        f.addRow(self.cb_ev_pay); f.addRow(self.cb_ev_vend)
        f.addRow(self.cb_ev_book); f.addRow(self.cb_ev_exp)
        f.addRow(QLabel("Подключение каналов:"))
        self.ed_max_tok = QLineEdit(); self.ed_max_tok.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_max_tok.setPlaceholderText("Токен бота MAX (выдаёт @masterbot)")
        self.lbl_max_st = QLabel("MAX: не проверено")
        bmax = QPushButton(" Сохранить токен MAX")
        bmax.clicked.connect(self.save_max_token)
        f.addRow(self.ed_max_tok); f.addRow(self.lbl_max_st); f.addRow(bmax)
        self.ed_tg_tok = QLineEdit(); self.ed_tg_tok.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_tg_tok.setPlaceholderText("Токен Telegram-бота (от @BotFather)")
        self.lbl_tg_st = QLabel("Telegram: не проверено")
        btg = QPushButton(" Подключить Telegram")
        btg.clicked.connect(self.save_telegram_token)
        f.addRow(self.ed_tg_tok); f.addRow(self.lbl_tg_st); f.addRow(btg)
        b = QPushButton(" Сохранить «Клиенту»")
        b.clicked.connect(self.save_client_settings)
        f.addRow(b)
        self.tabs.addTab(w, " Клиенту")
        _idx = self.tabs.indexOf(w)
        self.tabs.currentChanged.connect(lambda i, _i=_idx: i == _i and self._cn_load_tokens())

    def save_client_settings(self):
        payload = {
            "client_notify_enabled": self.cb_cn.isChecked(),
            "cn_max": self.cb_cn_max.isChecked(),
            "cn_telegram": self.cb_cn_tg.isChecked(),
            "cn_sms": self.cb_cn_sms.isChecked(),
            "cn_ev_payment": self.cb_ev_pay.isChecked(),
            "cn_ev_vending": self.cb_ev_vend.isChecked(),
            "cn_ev_booking": self.cb_ev_book.isChecked(),
            "cn_ev_expiry": self.cb_ev_exp.isChecked(),
        }
        try:
            fn = getattr(self.api, "put", None) or getattr(self.api, "post", None)
            if fn is None:
                raise RuntimeError("api-клиент без put/post")
            r = fn("/api/v1/notify/client-settings", json=payload)
            code = getattr(r, "status_code", 200)
            if code < 300:
                QMessageBox.information(self, "Клиенту", "Настройки сохранены.")
            else:
                QMessageBox.warning(self, "Клиенту", f"Сервер вернул {code}")
        except Exception as e:
            QMessageBox.warning(self, "Клиенту", f"Ошибка сохранения: {e}")

    def load_client_settings(self):
        try:
            fn = getattr(self.api, "get", None) or getattr(self.api, "request", None)
            if fn is None:
                return
            r = fn("/api/v1/notify/client-settings")
            data = r if isinstance(r, dict) else (r.json() if hasattr(r, "json") else {})
            self.cb_cn.setChecked(bool(data.get("enabled")))
            self.cb_cn_max.setChecked(bool(data.get("max")))
            self.cb_cn_tg.setChecked(bool(data.get("telegram")))
            self.cb_cn_sms.setChecked(bool(data.get("sms")))
            ev = data.get("events") or {}
            self.cb_ev_pay.setChecked(bool(ev.get("payment", True)))
            self.cb_ev_vend.setChecked(bool(ev.get("vending", True)))
            self.cb_ev_book.setChecked(bool(ev.get("booking_reminder", True)))
            self.cb_ev_exp.setChecked(bool(ev.get("subscription_expiry", True)))
            self._cn_load_tokens()
        except Exception:
            pass

    def _cn_request(self, method, path, payload=None):
        try:
            if hasattr(self.api, "session") and hasattr(self.api, "_url"):
                r = self.api.session.request(method, self.api._url(path), json=payload, timeout=20)
                return r.status_code, (r.json() if r.content else {})
            fn = getattr(self.api, method.lower(), None)
            if fn is None:
                return 0, {"error": "api-клиент не поддерживает " + method}
            r = fn(path, json=payload) if payload is not None else fn(path)
            return getattr(r, "status_code", 200), (r if isinstance(r, dict) else r.json())
        except Exception as e:
            return 0, {"error": str(e)[:150]}

    def save_max_token(self):
        tok = self.ed_max_tok.text().strip()
        if not tok:
            QMessageBox.warning(self, "MAX", "Введите токен бота.")
            return
        code, data = self._cn_request("POST", "/max-bot/config", {"bot_token": tok})
        if code < 300:
            self.ed_max_tok.clear()
            self._cn_load_tokens()
            QMessageBox.information(self, "MAX", "Токен сохранён, webhook подписан автоматически.")
        else:
            QMessageBox.warning(self, "MAX", "Ошибка: %s" % data)

    def save_telegram_token(self):
        tok = self.ed_tg_tok.text().strip()
        if not tok:
            QMessageBox.warning(self, "Telegram", "Введите токен бота.")
            return
        code, data = self._cn_request("POST", "/telegram/setup", {"token": tok})
        if code < 300:
            self.ed_tg_tok.clear()
            self._cn_load_tokens()
            QMessageBox.information(self, "Telegram", "Бот подключён, webhook установлен.")
        else:
            QMessageBox.warning(self, "Telegram", "Ошибка: %s" % data)

    def _cn_load_tokens(self):
        code, d = self._cn_request("GET", "/max-bot/config")
        if code < 300:
            self.lbl_max_st.setText("MAX: " + ("подключён (…%s)" % d.get("bot_token_tail")
                                               if d.get("bot_token_set") else "токен не задан"))
        else:
            self.lbl_max_st.setText("MAX: ошибка %s %s" % (code, d))
        code, d = self._cn_request("GET", "/telegram/webhook-info")
        if code < 300:
            self.lbl_tg_st.setText("Telegram: " + ("подключён" if d.get("is_active")
                                    else ("токен задан" if d.get("token_configured") else "не настроен")))
        else:
            self.lbl_tg_st.setText("Telegram: ошибка %s %s" % (code, d))

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
        b = QPushButton(" Сохранить SMS"); b.clicked.connect(lambda: self.save_settings("sms"))
        f.addRow(b)
        self.tabs.addTab(w, " SMS")

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
        b = QPushButton(" Сохранить Web Push"); b.clicked.connect(lambda: self.save_settings("push"))
        f.addRow(b)
        self.tabs.addTab(w, " Web Push")

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
        bt = QPushButton(" Отправить"); bt.clicked.connect(self.send_test)
        bd = QPushButton(" Отправить дайджест"); bd.clicked.connect(self.send_digest)
        hb2.addWidget(bt); hb2.addWidget(bd)
        f.addRow(hb2)
        self.tabs.addTab(w, " Отправка")

    def _build_log_tab(self):
        w = QWidget(); v = QVBoxLayout(w)
        b = QPushButton(" Обновить журнал"); b.clicked.connect(self.load_log)
        # 8 колонок: добавлены Дата и Время
        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Канал", "Кому", "Тема", "Дата", "Время", "Статус", "Ошибка"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        v.addWidget(b); v.addWidget(self.tbl)
        self.tabs.addTab(w, " Журнал")

    # ---------- логика ----------
    def _get(self, path):
        response = self.api.session.get(self.api._url(path), timeout=15)
        response.raise_for_status()
        return response.json()

    def _post(self, path, payload):
        response = self.api.session.post(self.api._url(path), json=payload, timeout=25)
        response.raise_for_status()
        return response.json()

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
            self.load_client_settings()
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
            QMessageBox.information(self, "Отправка",
                "Отправлено ✓" if r.get("ok") else f"Ошибка: {r.get('error')}")
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
            rows = rows if isinstance(rows, list) else []
            self.tbl.setRowCount(len(rows))
            for i, r in enumerate(rows):
                created = str(r.get("created_at") or "")
                date_s, _, time_s = created.partition("T")
                time_s = time_s[:8] if time_s else ""
                status_ru = STATUS_RU.get(str(r.get("status") or "").lower(),
                                          str(r.get("status") or ""))
                vals = [r.get("id"), r.get("channel"), r.get("recipient"),
                        r.get("subject"), date_s, time_s, status_ru, r.get("error")]
                for j, v in enumerate(vals):
                    self.tbl.setItem(i, j, QTableWidgetItem(str(v or "")))
        except Exception as e:
            print("[E17] log load:", e)