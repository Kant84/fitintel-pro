"""FitIntel Pro — Settings Tab (Super Admin edition)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QPlainTextEdit, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

import json, os, urllib.request


class SettingsTab(QWidget):
    def __init__(self, api=None, main_window=None):
        super().__init__()
        self.api = api
        self.mw = main_window
        self._role = self._detect_role()
        self._build_ui()
        self._sync_from_settings()

    # ── Role detection ──
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
        return self._role in ("admin", "superadmin", "super_admin", "owner")

    # ── Base / Token helpers (for raw requests) ──
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

    # ═══════════════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════════════
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Внешний вид (все) ──
        layout.addWidget(self._ui_appearance())

        # ── Подключение (все) ──
        layout.addWidget(self._ui_connection())

        # ── Email / SMTP (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_email())

        # ── SMS / smsc.ru (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_sms())

        # ── WebPush / VAPID (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_webpush())

        # ── YooKassa (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_yookassa())

        # ── MAX Bot (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_maxbot())

        # ── Бэкап БД (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_backup())

        # ── Лицензия (admin only) ──
        if self._is_admin():
            layout.addWidget(self._ui_license())

        # ── О программе (все) ──
        layout.addWidget(self._ui_about())

        # ── Логи (все) ──
        layout.addWidget(self._ui_logs())

        layout.addStretch()

    # ═══════════════════════════════════════════════════════
    #  SECTION: Appearance
    # ═══════════════════════════════════════════════════════
    def _ui_appearance(self):
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
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: Connection
    # ═══════════════════════════════════════════════════════
    def _ui_connection(self):
        box = QGroupBox("Подключение")
        form = QFormLayout(box)

        self.lbl_server = QLabel(getattr(self.api, "base_url", "http://localhost:8001/api/v1"))
        form.addRow("Сервер API:", self.lbl_server)

        b_check = QPushButton("Проверить связь")
        b_check.setStyleSheet("padding: 8px 16px; font-weight: 600;")
        b_check.clicked.connect(self._check)
        self.lbl_health = QLabel("—")
        form.addRow(b_check, self.lbl_health)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: Email / SMTP
    # ═══════════════════════════════════════════════════════
    def _ui_email(self):
        box = QGroupBox("📧  Email / SMTP (требуется для уведомлений и дайджестов)")
        form = QFormLayout(box)

        self.ed_smtp_host = QLineEdit()
        self.ed_smtp_host.setPlaceholderText("smtp.mail.ru")
        form.addRow("SMTP хост:", self.ed_smtp_host)

        self.ed_smtp_port = QSpinBox()
        self.ed_smtp_port.setRange(1, 65535)
        self.ed_smtp_port.setValue(465)
        form.addRow("SMTP порт:", self.ed_smtp_port)

        self.ed_smtp_user = QLineEdit()
        self.ed_smtp_user.setPlaceholderText("login@mail.ru")
        form.addRow("Логин:", self.ed_smtp_user)

        self.ed_smtp_pass = QLineEdit()
        self.ed_smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_smtp_pass.setPlaceholderText("пароль")
        form.addRow("Пароль:", self.ed_smtp_pass)

        self.ed_smtp_from = QLineEdit()
        self.ed_smtp_from.setPlaceholderText("FitIntel Pro <noreply@example.com>")
        form.addRow("Отправитель (From):", self.ed_smtp_from)

        btn = QPushButton("💾  Сохранить Email-настройки")
        btn.setStyleSheet("background: #ec4899; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn.clicked.connect(self._save_email)
        form.addRow(btn)

        self.lbl_email_status = QLabel("")
        self.lbl_email_status.setStyleSheet("font-size: 12px;")
        form.addRow(self.lbl_email_status)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: SMS
    # ═══════════════════════════════════════════════════════
    def _ui_sms(self):
        box = QGroupBox("📱  SMS / smsc.ru")
        form = QFormLayout(box)

        self.ed_smsc_login = QLineEdit()
        self.ed_smsc_login.setPlaceholderText("логин smsc.ru")
        form.addRow("SMSC логин:", self.ed_smsc_login)

        self.ed_smsc_pass = QLineEdit()
        self.ed_smsc_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_smsc_pass.setPlaceholderText("пароль smsc.ru")
        form.addRow("SMSC пароль:", self.ed_smsc_pass)

        self.ed_smsc_sender = QLineEdit()
        self.ed_smsc_sender.setPlaceholderText("FitIntel")
        form.addRow("Подпись отправителя:", self.ed_smsc_sender)

        btn = QPushButton("💾  Сохранить SMS-настройки")
        btn.setStyleSheet("background: #ec4899; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn.clicked.connect(self._save_sms)
        form.addRow(btn)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: WebPush / VAPID
    # ═══════════════════════════════════════════════════════
    def _ui_webpush(self):
        box = QGroupBox("🌐  Web Push / VAPID (браузерные уведомления)")
        form = QFormLayout(box)

        self.ed_vapid_pub = QLineEdit()
        self.ed_vapid_pub.setPlaceholderText("BCkR9...")
        form.addRow("VAPID Public Key:", self.ed_vapid_pub)

        self.ed_vapid_priv = QLineEdit()
        self.ed_vapid_priv.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_vapid_priv.setPlaceholderText("приватный ключ...")
        form.addRow("VAPID Private Key:", self.ed_vapid_priv)

        self.ed_vapid_sub = QLineEdit()
        self.ed_vapid_sub.setPlaceholderText("mailto:admin@fitintel.local")
        form.addRow("VAPID Subscriber:", self.ed_vapid_sub)

        btn = QPushButton("💾  Сохранить WebPush-настройки")
        btn.setStyleSheet("background: #ec4899; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn.clicked.connect(self._save_webpush)
        form.addRow(btn)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: YooKassa
    # ═══════════════════════════════════════════════════════
    def _ui_yookassa(self):
        box = QGroupBox("💳  YooKassa (платёжная система)")
        form = QFormLayout(box)

        self.ed_yk_shop = QLineEdit()
        self.ed_yk_shop.setPlaceholderText("123456")
        form.addRow("Shop ID:", self.ed_yk_shop)

        self.ed_yk_secret = QLineEdit()
        self.ed_yk_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_yk_secret.setPlaceholderText("live_...")
        form.addRow("Secret Key:", self.ed_yk_secret)

        btn = QPushButton("💾  Сохранить YooKassa")
        btn.setStyleSheet("background: #ec4899; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn.clicked.connect(self._save_yookassa)
        form.addRow(btn)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: MAX Bot
    # ═══════════════════════════════════════════════════════
    def _ui_maxbot(self):
        box = QGroupBox("💬  MAX Bot (MAX Messenger)")
        form = QFormLayout(box)

        self.ed_max_token = QLineEdit()
        self.ed_max_token.setPlaceholderText("токен из MAX API")
        form.addRow("MAX Bot Token:", self.ed_max_token)

        self.ed_max_url = QLineEdit()
        self.ed_max_url.setPlaceholderText("https://api.max.ru")
        form.addRow("MAX API URL:", self.ed_max_url)

        btn = QPushButton("💾  Сохранить MAX-настройки")
        btn.setStyleSheet("background: #ec4899; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn.clicked.connect(self._save_maxbot)
        form.addRow(btn)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: Backup
    # ═══════════════════════════════════════════════════════
    def _ui_backup(self):
        box = QGroupBox("💾  Резервное копирование БД")
        form = QFormLayout(box)

        self.ed_backup_path = QLineEdit()
        self.ed_backup_path.setPlaceholderText("C:\\backup\\fitintel")
        form.addRow("Путь для бэкапов:", self.ed_backup_path)

        self.ed_backup_cron = QLineEdit()
        self.ed_backup_cron.setPlaceholderText("0 3 * * *  (ежедневно в 03:00)")
        form.addRow("Расписание (cron):", self.ed_backup_cron)

        btn_now = QPushButton("🔄  Бэкап сейчас")
        btn_now.setStyleSheet("background: #06b6d4; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn_now.clicked.connect(self._backup_now)
        form.addRow(btn_now)

        self.lbl_backup_status = QLabel("")
        self.lbl_backup_status.setStyleSheet("font-size: 12px;")
        form.addRow(self.lbl_backup_status)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: License
    # ═══════════════════════════════════════════════════════
    def _ui_license(self):
        box = QGroupBox("🔐  Лицензия")
        form = QFormLayout(box)

        self.ed_license_key = QLineEdit()
        self.ed_license_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        form.addRow("Лицензионный ключ:", self.ed_license_key)

        btn_check = QPushButton("🔍  Проверить лицензию")
        btn_check.setStyleSheet("background: #8b5cf6; color: white; padding: 10px; font-weight: 600; border-radius: 8px;")
        btn_check.clicked.connect(self._check_license)
        form.addRow(btn_check)

        self.lbl_license_status = QLabel("—")
        self.lbl_license_status.setStyleSheet("font-size: 12px;")
        form.addRow("Статус:", self.lbl_license_status)
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: About
    # ═══════════════════════════════════════════════════════
    def _ui_about(self):
        box = QGroupBox("О программе")
        fl = QFormLayout(box)
        fl.addRow("Версия:", QLabel("FitIntel Pro Desktop v1.3.1"))
        fl.addRow("Платформа:", QLabel("PyQt6 thin client"))
        return box

    # ═══════════════════════════════════════════════════════
    #  SECTION: Logs
    # ═══════════════════════════════════════════════════════
    def _ui_logs(self):
        box = QGroupBox("Логи")
        fl = QFormLayout(box)
        try:
            from app_logging import LOG_FILE, LOG_DIR
            self.lbl_log = QLabel(str(LOG_FILE))
        except Exception:
            from pathlib import Path
            self.lbl_log = QLabel(str(Path("logs") / "client.log"))
        self.lbl_log.setStyleSheet("font-size: 11px;")
        self.lbl_log.setWordWrap(True)
        fl.addRow("Файл лога:", self.lbl_log)

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
        fl.addRow(row_log)

        self.lbl_tail = QLabel("")
        self.lbl_tail.setWordWrap(True)
        self.lbl_tail.setStyleSheet("font-size: 11px; color: #b91c1c;")
        fl.addRow(self.lbl_tail)
        return box

    # ═══════════════════════════════════════════════════════
    #  ACTIONS
    # ═══════════════════════════════════════════════════════
    def _sync_from_settings(self):
        if not self.mw:
            return
        st = getattr(self.mw, "ui_settings", {})
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

    def _save_email(self):
        r = self._req("POST", "/notify/settings", {
            "email_enabled": True,
            "smtp_host": self.ed_smtp_host.text(),
            "smtp_port": self.ed_smtp_port.value(),
            "smtp_user": self.ed_smtp_user.text(),
            "smtp_pass": self.ed_smtp_pass.text(),
            "email_from": self.ed_smtp_from.text(),
        })
        self._show_save_status(r, "Email")

    def _save_sms(self):
        r = self._req("POST", "/notify/settings", {
            "sms_enabled": True,
            "smsc_login": self.ed_smsc_login.text(),
            "smsc_pass": self.ed_smsc_pass.text(),
            "smsc_sender": self.ed_smsc_sender.text(),
        })
        self._show_save_status(r, "SMS")

    def _save_webpush(self):
        r = self._req("POST", "/notify/settings", {
            "webpush_enabled": True,
            "vapid_public": self.ed_vapid_pub.text(),
            "vapid_private": self.ed_vapid_priv.text(),
            "vapid_sub": self.ed_vapid_sub.text(),
        })
        self._show_save_status(r, "WebPush")

    def _save_yookassa(self):
        # YooKassa settings may have a separate endpoint; fallback to generic
        QMessageBox.information(self, "YooKassa", "YooKassa настройки сохраняются в .env сервера.\nИзмените SHOP_ID и SECRET_KEY в .env и перезапустите сервер.")

    def _save_maxbot(self):
        # MAX Bot token is server-side via .env
        QMessageBox.information(self, "MAX Bot", "MAX Bot токен сохраняется в .env сервера.\nИзмените MAX_BOT_TOKEN в .env и перезапустите сервер.")

    def _backup_now(self):
        r = self._req("POST", "/backup/run", {})
        if isinstance(r, dict) and "_err" not in r:
            self.lbl_backup_status.setText("✅ Бэкап запущен")
            self.lbl_backup_status.setStyleSheet("color: #059669;")
        else:
            self.lbl_backup_status.setText(f"❌ Ошибка: {r.get('_body', str(r))}")
            self.lbl_backup_status.setStyleSheet("color: #ef4444;")

    def _check_license(self):
        key = self.ed_license_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Лицензия", "Введите ключ")
            return
        r = self._req("POST", "/license/validate", {"license_key": key})
        if isinstance(r, dict) and "_err" not in r:
            self.lbl_license_status.setText(f"✅ {r.get('status', 'OK')}")
            self.lbl_license_status.setStyleSheet("color: #059669;")
        else:
            self.lbl_license_status.setText(f"❌ {r.get('_body', str(r))}")
            self.lbl_license_status.setStyleSheet("color: #ef4444;")

    def _show_save_status(self, r, name):
        if isinstance(r, dict) and "_err" not in r:
            QMessageBox.information(self, name, f"{name} настройки сохранены")
        else:
            QMessageBox.warning(self, name, f"Ошибка сохранения: {r.get('_body', str(r))}")

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