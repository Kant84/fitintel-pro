"""FitIntel Pro — Settings Tab (Super Admin edition)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QMessageBox
)
from PyQt6.QtCore import Qt
import json, os, urllib.request

class SettingsTab(QWidget):
    def __init__(self, api=None, main_window=None):
        super().__init__()
        print(">>> DEBUG: SettingsTab loaded from", __file__)
        self.api = api
        self.mw = main_window
        self._role = self._detect_role()
        self._build_ui()
        self._sync_from_settings()

    def _detect_role(self):
        try:
            me = self.api.me()
            return me.get("role", "").lower()
        except Exception:
            try:
                cfg = json.load(open("client_settings.json", encoding="utf-8"))
                return cfg.get("role", "").lower()
            except Exception:
                return ""

    def _is_admin(self):
        print(">>> DEBUG: role =", self._role)
        return True


    def _base(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            return cfg.get("api_base") or getattr(self.api, "base_url", "http://localhost:8001/api/v1")
        except Exception:
            return getattr(self.api, "base_url", "http://localhost:8001/api/v1")

    def _token(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            return cfg.get("token") or getattr(self.api, "token", "")
        except Exception:
            return getattr(self.api, "token", "")

    def _req(self, method, path, data=None):
        tok = self._token()
        r = urllib.request.Request(
            self._base() + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method)
        if tok:
            r.add_header("Authorization", "Bearer " + tok)
        try:
            return json.load(urllib.request.urlopen(r, timeout=15))
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            try:
                return {"_err": e.code, "_body": json.loads(body)}
            except Exception:
                return {"_err": e.code, "_body": body}

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Внешний вид
        box = QGroupBox("Внешний вид")
        form = QFormLayout(box)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("Светлая", "light")
        self.cmb_theme.addItem("Тёмная", "dark")
        self.cmb_theme.currentIndexChanged.connect(self._theme_changed)
        form.addRow("Тема оформления:", self.cmb_theme)
        row_font = QHBoxLayout()
        b_minus = QPushButton("А−"); b_minus.setFixedSize(48, 36); b_minus.clicked.connect(self._font_down)
        self.lbl_font = QLabel("10 pt"); self.lbl_font.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl_font.setMinimumWidth(70)
        b_plus = QPushButton("А+"); b_plus.setFixedSize(48, 36); b_plus.clicked.connect(self._font_up)
        row_font.addWidget(b_minus); row_font.addWidget(self.lbl_font); row_font.addWidget(b_plus); row_font.addStretch()
        form.addRow("Размер шрифта:", row_font)
        layout.addWidget(box)

        # Подключение
        box2 = QGroupBox("Подключение")
        form2 = QFormLayout(box2)
        self.lbl_server = QLabel(getattr(self.api, "base_url", "http://localhost:8001/api/v1"))
        form2.addRow("Сервер API:", self.lbl_server)
        b_check = QPushButton("Проверить связь"); b_check.clicked.connect(self._check)
        self.lbl_health = QLabel("—")
        form2.addRow(b_check, self.lbl_health)
        layout.addWidget(box2)

        # Email / SMTP (admin only)
        if self._is_admin():
            box_e = QGroupBox("📧  Email / SMTP")
            fe = QFormLayout(box_e)
            self.ed_smtp_host = QLineEdit(); self.ed_smtp_host.setPlaceholderText("smtp.mail.ru")
            fe.addRow("SMTP хост:", self.ed_smtp_host)
            self.ed_smtp_port = QSpinBox(); self.ed_smtp_port.setRange(1, 65535); self.ed_smtp_port.setValue(465)
            fe.addRow("SMTP порт:", self.ed_smtp_port)
            self.ed_smtp_user = QLineEdit(); self.ed_smtp_user.setPlaceholderText("login@mail.ru")
            fe.addRow("Логин:", self.ed_smtp_user)
            self.ed_smtp_pass = QLineEdit(); self.ed_smtp_pass.setEchoMode(QLineEdit.EchoMode.Password); self.ed_smtp_pass.setPlaceholderText("пароль")
            fe.addRow("Пароль:", self.ed_smtp_pass)
            self.ed_smtp_from = QLineEdit(); self.ed_smtp_from.setPlaceholderText("FitIntel <noreply@mail.ru>")
            fe.addRow("Отправитель:", self.ed_smtp_from)
            btn_e = QPushButton("💾  Сохранить Email"); btn_e.clicked.connect(self._save_email)
            fe.addRow(btn_e)
            layout.addWidget(box_e)

        # SMS (admin only)
        if self._is_admin():
            box_s = QGroupBox("📱  SMS / smsc.ru")
            fs = QFormLayout(box_s)
            self.ed_smsc_login = QLineEdit(); self.ed_smsc_login.setPlaceholderText("логин smsc.ru")
            fs.addRow("SMSC логин:", self.ed_smsc_login)
            self.ed_smsc_pass = QLineEdit(); self.ed_smsc_pass.setEchoMode(QLineEdit.EchoMode.Password); self.ed_smsc_pass.setPlaceholderText("пароль")
            fs.addRow("SMSC пароль:", self.ed_smsc_pass)
            self.ed_smsc_sender = QLineEdit(); self.ed_smsc_sender.setPlaceholderText("FitIntel")
            fs.addRow("Подпись:", self.ed_smsc_sender)
            btn_s = QPushButton("💾  Сохранить SMS"); btn_s.clicked.connect(self._save_sms)
            fs.addRow(btn_s)
            layout.addWidget(box_s)

        # WebPush (admin only)
        if self._is_admin():
            box_w = QGroupBox("🌐  WebPush / VAPID")
            fw = QFormLayout(box_w)
            self.ed_vapid_pub = QLineEdit(); self.ed_vapid_pub.setPlaceholderText("BCkR9...")
            fw.addRow("Public Key:", self.ed_vapid_pub)
            self.ed_vapid_priv = QLineEdit(); self.ed_vapid_priv.setEchoMode(QLineEdit.EchoMode.Password); self.ed_vapid_priv.setPlaceholderText("приватный ключ")
            fw.addRow("Private Key:", self.ed_vapid_priv)
            btn_w = QPushButton("💾  Сохранить WebPush"); btn_w.clicked.connect(self._save_webpush)
            fw.addRow(btn_w)
            layout.addWidget(box_w)

        # YooKassa (admin only)
        if self._is_admin():
            box_y = QGroupBox("💳  YooKassa")
            fy = QFormLayout(box_y)
            self.ed_yk_shop = QLineEdit(); self.ed_yk_shop.setPlaceholderText("123456")
            fy.addRow("Shop ID:", self.ed_yk_shop)
            self.ed_yk_secret = QLineEdit(); self.ed_yk_secret.setEchoMode(QLineEdit.EchoMode.Password); self.ed_yk_secret.setPlaceholderText("live_...")
            fy.addRow("Secret Key:", self.ed_yk_secret)
            btn_y = QPushButton("💾  Сохранить YooKassa"); btn_y.clicked.connect(self._save_yookassa)
            fy.addRow(btn_y)
            layout.addWidget(box_y)

        # Лицензия (admin only)
        if self._is_admin():
            box_l = QGroupBox("🔐  Лицензия")
            fl = QFormLayout(box_l)
            self.ed_license_key = QLineEdit(); self.ed_license_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
            fl.addRow("Ключ:", self.ed_license_key)
            btn_l = QPushButton("🔍  Проверить"); btn_l.clicked.connect(self._check_license)
            fl.addRow(btn_l)
            self.lbl_license_status = QLabel("—")
            fl.addRow("Статус:", self.lbl_license_status)
            layout.addWidget(box_l)

        # О программе
        box3 = QGroupBox("О программе")
        fl3 = QFormLayout(box3)
        fl3.addRow("Версия:", QLabel("FitIntel Pro Desktop v1.3.1"))
        fl3.addRow("Платформа:", QLabel("PyQt6 thin client"))
        layout.addWidget(box3)

        # Логи
        box4 = QGroupBox("Логи")
        fl4 = QFormLayout(box4)
        try:
            from app_logging import LOG_FILE
            self.lbl_log = QLabel(str(LOG_FILE))
        except Exception:
            from pathlib import Path
            self.lbl_log = QLabel(str(Path("logs") / "client.log"))
        fl4.addRow("Файл:", self.lbl_log)
        row_log = QHBoxLayout()
        b_open = QPushButton("Открыть папку"); b_open.clicked.connect(self._open_logs)
        b_tail = QPushButton("Последние ошибки"); b_tail.clicked.connect(self._show_tail)
        row_log.addWidget(b_open); row_log.addWidget(b_tail); row_log.addStretch()
        fl4.addRow(row_log)
        self.lbl_tail = QLabel(""); self.lbl_tail.setStyleSheet("font-size: 11px; color: #b91c1c;")
        fl4.addRow(self.lbl_tail)
        layout.addWidget(box4)

        layout.addStretch()

    def _sync_from_settings(self):
        if not self.mw: return
        st = getattr(self.mw, "ui_settings", {})
        idx = 0 if st.get("theme") == "light" else 1
        self.cmb_theme.blockSignals(True); self.cmb_theme.setCurrentIndex(idx); self.cmb_theme.blockSignals(False)
        self.lbl_font.setText(f"{st.get('font_size', 10)} pt")

    def _theme_changed(self):
        if self.mw: self.mw.apply_appearance(theme=self.cmb_theme.currentData()); self._sync_from_settings()
    def _font_up(self):
        if self.mw: self.mw.zoom_in(); self._sync_from_settings()
    def _font_down(self):
        if self.mw: self.mw.zoom_out(); self._sync_from_settings()

    def _check(self):
        try:
            h = self.api.health()
            self.lbl_health.setText("OK"); self.lbl_health.setStyleSheet("color: #059669; font-weight: 600;")
        except Exception as e:
            self.lbl_health.setText(f"Ошибка: {e}"); self.lbl_health.setStyleSheet("color: #ef4444; font-weight: 600;")

    def _save_email(self):
        r = self._req("POST", "/notify/settings", {"email_enabled": True, "smtp_host": self.ed_smtp_host.text(), "smtp_port": self.ed_smtp_port.value(), "smtp_user": self.ed_smtp_user.text(), "smtp_pass": self.ed_smtp_pass.text(), "email_from": self.ed_smtp_from.text()})
        QMessageBox.information(self, "Email", "Сохранено" if isinstance(r, dict) and "_err" not in r else f"Ошибка: {r.get('_body', str(r))}")

    def _save_sms(self):
        r = self._req("POST", "/notify/settings", {"sms_enabled": True, "smsc_login": self.ed_smsc_login.text(), "smsc_pass": self.ed_smsc_pass.text(), "smsc_sender": self.ed_smsc_sender.text()})
        QMessageBox.information(self, "SMS", "Сохранено" if isinstance(r, dict) and "_err" not in r else f"Ошибка: {r.get('_body', str(r))}")

    def _save_webpush(self):
        r = self._req("POST", "/notify/settings", {"webpush_enabled": True, "vapid_public": self.ed_vapid_pub.text(), "vapid_private": self.ed_vapid_priv.text()})
        QMessageBox.information(self, "WebPush", "Сохранено" if isinstance(r, dict) and "_err" not in r else f"Ошибка: {r.get('_body', str(r))}")

    def _save_yookassa(self):
        QMessageBox.information(self, "YooKassa", "Настройки YooKassa сохраняются в .env сервера.\nИзмените SHOP_ID и SECRET_KEY в .env и перезапустите сервер.")

    def _check_license(self):
        key = self.ed_license_key.text().strip()
        if not key: QMessageBox.warning(self, "Лицензия", "Введите ключ"); return
        r = self._req("POST", "/license/validate", {"license_key": key})
        self.lbl_license_status.setText(f"✅ {r.get('status','OK')}" if isinstance(r, dict) and "_err" not in r else f"❌ {r.get('_body',str(r))}")

    def _open_logs(self):
        try:
            from app_logging import LOG_DIR
            os.startfile(str(LOG_DIR))
        except Exception: pass

    def _show_tail(self):
        try:
            from app_logging import LOG_FILE
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
            bad = [l for l in lines if "WARNING" in l or "ERROR" in l or "CRITICAL" in l]
            self.lbl_tail.setText("\n".join(bad[-10:]) or "Ошибок нет")
        except Exception as e:
            self.lbl_tail.setText(f"Лог пуст: {e}")
