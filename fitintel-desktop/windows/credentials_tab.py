"""E15: Браслеты и карты доступа — интеграция со СКУД (ITC-30, S80F, онлайн-замки)."""
import json, urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox,
    QLineEdit, QGroupBox, QFormLayout, QSpinBox, QPlainTextEdit,
    QTabWidget, QSplitter, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

STYLE_DARK = """
QWidget { background-color: #0f172a; color: #e2e8f0; font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }
QGroupBox { border: 1px solid #334155; border-radius: 10px; margin-top: 12px; padding-top: 10px; font-weight: 600; color: #06b6d4; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; }
QLineEdit, QComboBox, QSpinBox { background: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 8px 12px; color: #f1f5f9; selection-background-color: #ec4899; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #ec4899; }
QPushButton { border: none; border-radius: 8px; padding: 10px 18px; font-weight: 600; color: white; }
QPushButton:hover { opacity: 0.85; }
QPushButton:pressed { opacity: 0.7; }
QPlainTextEdit { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 8px; color: #94a3b8; font-family: "Consolas", monospace; }
QTableWidget { background: #1e293b; border: 1px solid #334155; border-radius: 8px; gridline-color: #334155; color: #e2e8f0; }
QTableWidget::item:selected { background: #ec4899; color: white; }
QHeaderView::section { background: #1e293b; color: #06b6d4; padding: 8px; border: none; font-weight: 600; }
QLabel { color: #cbd5e1; }
"""

BTN_PRIMARY   = "background: linear-gradient(135deg, #ec4899, #be185d);"
BTN_SECONDARY = "background: linear-gradient(135deg, #06b6d4, #0891b2);"
BTN_SUCCESS   = "background: linear-gradient(135deg, #10b981, #059669);"
BTN_WARNING   = "background: linear-gradient(135deg, #f59e0b, #d97706);"
BTN_DANGER    = "background: linear-gradient(135deg, #ef4444, #dc2626);"
BTN_PURPLE    = "background: linear-gradient(135deg, #8b5cf6, #7c3aed);"

# Kerong S80F / ITC-S80F форматы
EMPTY_CARD    = "025D000000000000000000000000005F"
ADMIN_CARD    = "02000000000000000000000001000003"
TRAILER_ITC   = "000000000000FF078069666666666666"
KEY_A_ITC     = "FFFFFFFFFFFF"
KEY_B_ITC     = "666666666666"


def _encode_locknum(num: int) -> str:
    return f"020B000000{num:02X}00000000000000000003"


class CredentialsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        self.setStyleSheet(STYLE_DARK)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._client_tab(), "👤  Клиентская карта")
        tabs.addTab(self._admin_tab(), "🔧  Программирование замков")
        tabs.addTab(self._online_tab(), "☁️  Онлайн-замки")
        lay.addWidget(tabs)

    def _base(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            return cfg.get("api_base") or "http://localhost:8001/api/v1"
        except Exception:
            return "http://localhost:8001/api/v1"

    def _token(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            r = urllib.request.Request(
                self._base() + "/auth/login",
                data=json.dumps({"login": cfg.get("saved_login"),
                                 "password": cfg.get("saved_password")}).encode(),
                headers={"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(r, timeout=10)).get("access_token")
        except Exception:
            return None

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

    def _log(self, widget, msg):
        widget.appendPlainText(msg)

    def _client_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        top = QHBoxLayout()
        self.client_search = QLineEdit()
        self.client_search.setPlaceholderText("🔍  ФИО, телефон или ID клиента...")
        self.client_search.returnPressed.connect(self._search_client)
        top.addWidget(self.client_search, 4)
        b_search = QPushButton("Найти")
        b_search.setStyleSheet(BTN_SECONDARY)
        b_search.clicked.connect(self._search_client)
        top.addWidget(b_search, 1)
        self.vendor = QComboBox()
        self.vendor.addItems(["KERONG", "Gantner", "ACS (PC/SC)"])
        self.vendor.currentIndexChanged.connect(self._update_models)
        top.addWidget(QLabel("Производитель:"))
        top.addWidget(self.vendor, 2)
        self.model = QComboBox()
        top.addWidget(QLabel("Модель:"))
        top.addWidget(self.model, 2)
        lay.addLayout(top)
        self._update_models()
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setSpacing(10)
        self.client_info = QGroupBox("👤  Клиент не выбран")
        fl = QFormLayout(self.client_info)
        fl.setSpacing(8)
        self.lbl_name  = QLabel("—")
        self.lbl_phone = QLabel("—")
        self.lbl_id    = QLabel("—")
        fl.addRow("ФИО:",     self.lbl_name)
        fl.addRow("Телефон:", self.lbl_phone)
        fl.addRow("ID:",      self.lbl_id)
        left_lay.addWidget(self.client_info)
        prog = QGroupBox("⚙️  Параметры записи")
        pfl = QFormLayout(prog)
        pfl.setSpacing(8)
        self.sector = QSpinBox()
        self.sector.setRange(0, 15)
        self.sector.setValue(0)
        pfl.addRow("Сектор:", self.sector)
        self.block = QSpinBox()
        self.block.setRange(0, 3)
        self.block.setValue(1)
        pfl.addRow("Блок:", self.block)
        left_lay.addWidget(prog)
        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(8)
        b_encode = QPushButton("🔷  Очистить носитель")
        b_encode.setStyleSheet(BTN_SECONDARY)
        b_encode.setToolTip("Записать пустые данные — карта станет 'Пустая карта'")
        b_encode.clicked.connect(self._encode_card)
        btn_grid.addWidget(b_encode)
        b_write = QPushButton("💾  Привязать к клиенту")
        b_write.setStyleSheet(BTN_PRIMARY)
        b_write.setToolTip("Считать UID и привязать к выбранному клиенту")
        b_write.clicked.connect(self._write_credential)
        btn_grid.addWidget(b_write)
        b_reset = QPushButton("🗑️  Сброс к заводским")
        b_reset.setStyleSheet(BTN_DANGER)
        b_reset.setToolTip("Полный сброс Mifare — factory default")
        b_reset.clicked.connect(self._reset_card)
        btn_grid.addWidget(b_reset)
        left_lay.addLayout(btn_grid)
        self.reader_status = QLabel("🔴  Считыватель не подключён")
        self.reader_status.setStyleSheet("color: #ef4444; font-weight: 600;")
        left_lay.addWidget(self.reader_status)
        b_check = QPushButton("🔍  Проверить считыватель")
        b_check.setStyleSheet(BTN_PURPLE)
        b_check.clicked.connect(self._check_reader)
        left_lay.addWidget(b_check)
        self.log = QPlainTextEdit()
        self.log.setMaximumBlockCount(100)
        self.log.setPlaceholderText("Журнал операций...")
        left_lay.addWidget(self.log, 1)
        split.addWidget(left)
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setSpacing(10)
        hdr = QLabel("<h4 style='color:#06b6d4;'>📋  Носители клиента</h4>")
        right_lay.addWidget(hdr)
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Тип", "ID / UID", "Статус", "Действителен до", "Модель"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setColumnWidth(0, 60)
        self.tbl.setColumnWidth(1, 140)
        self.tbl.setColumnWidth(2, 90)
        right_lay.addWidget(self.tbl, 1)
        b_refresh = QPushButton("🔄  Обновить список")
        b_refresh.setStyleSheet(BTN_SECONDARY)
        b_refresh.clicked.connect(self._load_credentials)
        right_lay.addWidget(b_refresh)
        split.addWidget(right)
        split.setSizes([520, 420])
        lay.addWidget(split, 1)
        self._current_client_id = None
        return w

    def _update_models(self):
        vendors = {
            "KERONG":      ["KR-S50", "KR-S80", "KR-S100", "KR-S100L", "KR-S300"],
            "Gantner":     ["GAT-Lock 2.0", "GAT-Lock 3.0"],
            "ACS (PC/SC)": ["ACR122U", "ACR1252", "OMNIKEY 5022"],
        }
        self.model.clear()
        self.model.addItems(vendors.get(self.vendor.currentText(), []))

    def _search_client(self):
        q = self.client_search.text().strip()
        if not q:
            return
        r = self._req("GET", "/clients?search=" + urllib.request.quote(q) + "&limit=5")
        items = r.get("items", []) if isinstance(r, dict) else []
        if not items:
            QMessageBox.information(self, "Поиск", "Клиенты не найдены")
            return
        c = items[0]
        self._current_client_id = c.get("id")
        ln = c.get("last_name", "")
        fn = c.get("first_name", "")
        mn = c.get("middle_name", "")
        self.lbl_name.setText((ln + " " + fn + " " + mn).strip())
        self.lbl_phone.setText(str(c.get("phone", "—")))
        self.lbl_id.setText(str(self._current_client_id))
        self.client_info.setTitle("👤  " + self.lbl_name.text())
        self._log(self.log, "✓ Выбран: " + self.lbl_name.text())
        self._load_credentials()

    def _load_credentials(self):
        if not self._current_client_id:
            return
        cid = str(self._current_client_id)
        self.tbl.setRowCount(0)
        r = self._req("GET", "/credentials/rfid/client/" + cid)
        if isinstance(r, dict) and "_err" not in r:
            rows = r.get("credentials", r.get("items", []))
            for row in rows:
                i = self.tbl.rowCount()
                self.tbl.insertRow(i)
                self.tbl.setItem(i, 0, QTableWidgetItem("RFID"))
                self.tbl.setItem(i, 1, QTableWidgetItem(str(row.get("credential_value", "—"))[:22]))
                self.tbl.setItem(i, 2, QTableWidgetItem(str(row.get("status", "—"))))
                self.tbl.setItem(i, 3, QTableWidgetItem(str(row.get("valid_until", "—"))))
                self.tbl.setItem(i, 4, QTableWidgetItem(str(row.get("rfid_model", ""))))

    def _encode_card(self):
        self._log(self.log, "🔷 Поднесите носитель для очистки...")
        r = self._req("POST", "/reader/detect-card")
        if isinstance(r, dict) and "_err" in r:
            self._log(self.log, "❌ Носитель не обнаружен")
            return
        r2 = self._req("POST", "/reader/write", {
            "sector": 0,
            "block": 1,
            "key_type": "B",
            "key_hex": KEY_B_ITC,
            "data_hex": EMPTY_CARD
        })
        if isinstance(r2, dict) and "_err" not in r2:
            self._log(self.log, "✅ Носитель очищен (Пустая карта ITC)")
        else:
            self._log(self.log, "❌ Ошибка: " + str(r2.get("_body", str(r2))))

    def _write_credential(self):
        if not self._current_client_id:
            QMessageBox.warning(self, "Клиент", "Сначала выберите клиента")
            return
        vendor = self.vendor.currentText()
        model = self.model.currentText()
        cid = str(self._current_client_id)
        self._log(self.log, "📖 Поднесите браслет / карту к считывателю...")
        self.reader_status.setText("🟡  Ожидание носителя...")
        self.reader_status.setStyleSheet("color: #f59e0b; font-weight: 600;")
        r_detect = self._req("POST", "/reader/detect-card")
        if isinstance(r_detect, dict) and "_err" in r_detect:
            self._log(self.log, "❌ Носитель не обнаружен")
            self.reader_status.setText("🔴  Носитель не найден")
            self.reader_status.setStyleSheet("color: #ef4444; font-weight: 600;")
            return
        uid = r_detect.get("uid")
        self._log(self.log, "✅ UID считан: " + str(uid))
        r = self._req("POST", "/credentials/rfid/force-write", {
            "client_id": cid,
            "credential_value": uid,
            "rfid_manufacturer": vendor,
            "rfid_model": model,
            "sector": self.sector.value(),
            "block": self.block.value()
        })
        if isinstance(r, dict) and "_err" not in r:
            self._log(self.log, "✅ Привязано: " + vendor + " " + model + ", UID=" + str(uid))
            self.reader_status.setText("🟢  Готово")
            self.reader_status.setStyleSheet("color: #10b981; font-weight: 600;")
            self._load_credentials()
        else:
            err = r.get("_body", {}) if isinstance(r, dict) else {}
            msg = err.get("detail", str(err)) if isinstance(err, dict) else str(err)
            self._log(self.log, "❌ Ошибка привязки: " + str(msg))
            self.reader_status.setText("🔴  Ошибка записи")
            self.reader_status.setStyleSheet("color: #ef4444; font-weight: 600;")

    def _reset_card(self):
        self._log(self.log, "🗑️ Поднесите носитель для сброса...")
        r = self._req("POST", "/reader/detect-card")
        if isinstance(r, dict) and "_err" in r:
            self._log(self.log, "❌ Носитель не обнаружен")
            return
        r2 = self._req("POST", "/reader/write", {
            "sector": 0,
            "block": 3,
            "key_type": "A",
            "key_hex": KEY_A_ITC,
            "data_hex": "ffffffffffffffffffffffff078069ff"
        })
        if isinstance(r2, dict) and "_err" not in r2:
            self._log(self.log, "✅ Носитель сброшен (factory default)")
        else:
            self._log(self.log, "❌ Ошибка сброса: " + str(r2.get("_body", str(r2))))

    def _check_reader(self):
        try:
            r = self._req("GET", "/reader/status")
            if r.get("connected"):
                self.reader_status.setText("🟢  " + str(r.get("reader_name", "Считыватель подключён")))
                self.reader_status.setStyleSheet("color: #10b981; font-weight: 600;")
            else:
                self.reader_status.setText("🔴  Считыватель не найден")
                self.reader_status.setStyleSheet("color: #ef4444; font-weight: 600;")
        except Exception as e:
            self.reader_status.setText("🔴  " + str(e)[:50])
            self.reader_status.setStyleSheet("color: #ef4444; font-weight: 600;")

    def _admin_tab(self):
        w = QWidget()
        w.setStyleSheet(STYLE_DARK)
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(QLabel("<h3 style='color:#ec4899;'>🔧  Программирование оффлайн-замков Kerong S80F</h3>"))
        top = QHBoxLayout()
        self.admin_sector = QSpinBox()
        self.admin_sector.setRange(0, 2)
        self.admin_sector.setValue(0)
        top.addWidget(QLabel("Рабочий сектор:"))
        top.addWidget(self.admin_sector)
        self.lock_num = QLineEdit()
        self.lock_num.setPlaceholderText("Номер шкафчика...")
        top.addWidget(self.lock_num)
        top.addStretch(1)
        lay.addLayout(top)
        grid = QHBoxLayout()
        grid.setSpacing(10)
        def make_btn(text, color, cmd):
            b = QPushButton(text)
            b.setStyleSheet(color)
            b.setMinimumHeight(48)
            b.clicked.connect(lambda: self._admin_cmd(cmd))
            return b
        col1 = QVBoxLayout()
        col1.setSpacing(8)
        col1.addWidget(make_btn("🔷  Очистить носитель", BTN_SECONDARY, "encode"))
        col1.addWidget(make_btn("🗑️  Сброс к заводским", BTN_DANGER, "reset_card"))
        col1.addWidget(make_btn("📖  Прочитать карту", BTN_PURPLE, "read"))
        grid.addLayout(col1)
        col2 = QVBoxLayout()
        col2.setSpacing(8)
        col2.addWidget(make_btn("🛡️  Карта доступа", BTN_PURPLE, "auth_card"))
        col2.addWidget(make_btn("👑  Мастер-карта", BTN_PRIMARY, "admin_card"))
        col2.addWidget(make_btn("🔢  Назначить номер", BTN_SUCCESS, "assign_num"))
        grid.addLayout(col2)
        col3 = QVBoxLayout()
        col3.setSpacing(8)
        col3.addWidget(make_btn("🔐  Режим личный", BTN_PURPLE, "individual"))
        col3.addWidget(make_btn("🚫  Очистить замок", BTN_WARNING, "remove_mode"))
        col3.addWidget(make_btn("📋  Клонировать", BTN_SECONDARY, "clone"))
        grid.addLayout(col3)
        col4 = QVBoxLayout()
        col4.setSpacing(8)
        col4.addStretch(1)
        b_reset_lock = make_btn("💥  Перезагрузить замок", BTN_DANGER, "reset_lock")
        b_reset_lock.setMinimumHeight(100)
        col4.addWidget(b_reset_lock)
        grid.addLayout(col4)
        lay.addLayout(grid)
        self.admin_log = QPlainTextEdit()
        self.admin_log.setMaximumBlockCount(100)
        self.admin_log.setPlaceholderText("Журнал программирования...")
        lay.addWidget(self.admin_log, 1)
        return w

    def _admin_cmd(self, cmd):
        log = self.admin_log
        sector = self.admin_sector.value()
        lock_num = self.lock_num.text().strip()
        if cmd == "encode":
            data_hex, block, ktype, khex = EMPTY_CARD, 1, "B", KEY_B_ITC
        elif cmd == "reset_card":
            data_hex, block, ktype, khex = "ffffffffffffffffffffffff078069ff", 3, "A", KEY_A_ITC
        elif cmd == "admin_card":
            data_hex, block, ktype, khex = ADMIN_CARD, 1, "B", KEY_B_ITC
        elif cmd == "assign_num":
            try:
                num = int(lock_num)
                data_hex, block, ktype, khex = _encode_locknum(num), 1, "B", KEY_B_ITC
            except ValueError:
                log.appendPlainText("❌ Введите номер шкафчика")
                return
        elif cmd == "auth_card":
            data_hex, block, ktype, khex = "02000000000000000000000000000003", 1, "B", KEY_B_ITC
        elif cmd == "individual":
            data_hex, block, ktype, khex = "02010000000000000000000000000003", 1, "B", KEY_B_ITC
        elif cmd == "remove_mode":
            data_hex, block, ktype, khex = "02020000000000000000000000000003", 1, "B", KEY_B_ITC
        elif cmd == "reset_lock":
            data_hex, block, ktype, khex = "02030000000000000000000000000003", 1, "B", KEY_B_ITC
        elif cmd == "read":
            self._read_card_admin(log)
            return
        elif cmd == "clone":
            self._clone_card_admin(log)
            return
        else:
            data_hex, block, ktype, khex = "0" * 32, 1, "A", KEY_A_ITC
        log.appendPlainText("▶ " + cmd + "  |  сектор " + str(sector) + "  |  блок " + str(block))
        log.appendPlainText("  Поднесите карту к считывателю...")
        r = self._req("POST", "/reader/detect-card")
        if isinstance(r, dict) and "_err" in r:
            log.appendPlainText("  ❌ Карта не обнаружена")
            return
        r2 = self._req("POST", "/reader/write", {
            "sector": sector,
            "block": block,
            "key_type": ktype,
            "key_hex": khex,
            "data_hex": data_hex
        })
        if isinstance(r2, dict) and "_err" not in r2:
            log.appendPlainText("  ✅ Команда записана: " + data_hex[:16] + "...")
            if cmd == "assign_num" and lock_num:
                self.lock_num.setText(str(int(lock_num) + 1))
        else:
            log.appendPlainText("  ❌ Ошибка: " + str(r2.get("_body", str(r2))))

    def _read_card_admin(self, log):
        log.appendPlainText("📖 Поднесите носитель для чтения...")
        r = self._req("POST", "/reader/read-sector", {
            "sector": 0,
            "key_type": "B",
            "key_hex": KEY_B_ITC
        })
        if isinstance(r, dict) and "_err" not in r:
            blocks = r.get("blocks", {})
            for k, v in blocks.items():
                log.appendPlainText("  " + k + ": " + str(v))
            b1 = blocks.get("block_1", "")
            if b1.startswith("020B"):
                num = int(b1[10:12], 16)
                log.appendPlainText("  🔒 Номер шкафчика: " + str(num))
            elif b1 == ADMIN_CARD:
                log.appendPlainText("  👤 Администратор")
            elif b1 == EMPTY_CARD:
                log.appendPlainText("  🔓 Пустая карта")
            else:
                log.appendPlainText("  📝 Raw: " + str(b1))
        else:
            log.appendPlainText("  ❌ Ошибка чтения: " + str(r.get("_body", str(r))))

    def _clone_card_admin(self, log):
        log.appendPlainText("📋 Поднесите ИСХОДНУЮ карту...")
        r = self._req("POST", "/reader/read-sector", {
            "sector": 0,
            "key_type": "B",
            "key_hex": KEY_B_ITC
        })
        if isinstance(r, dict) and "_err" in r:
            log.appendPlainText("  ❌ Не удалось прочитать")
            return
        src = r.get("blocks", {}).get("block_1", "")
        log.appendPlainText("  Исходный block_1: " + str(src))
        log.appendPlainText("  Поднесите ЦЕЛЕВУЮ карту...")
        r2 = self._req("POST", "/reader/detect-card")
        if isinstance(r2, dict) and "_err" in r2:
            log.appendPlainText("  ❌ Целевая карта не обнаружена")
            return
        r3 = self._req("POST", "/reader/write", {
            "sector": 0,
            "block": 1,
            "key_type": "B",
            "key_hex": KEY_B_ITC,
            "data_hex": src
        })
        if isinstance(r3, dict) and "_err" not in r3:
            log.appendPlainText("  ✅ Клонирование завершено")
        else:
            log.appendPlainText("  ❌ Ошибка записи: " + str(r3.get("_body", str(r3))))

    def _online_tab(self):
        w = QWidget()
        w.setStyleSheet(STYLE_DARK)
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(QLabel("<h3 style='color:#06b6d4;'>☁️  Управление онлайн-замками</h3>"))
        f = QFormLayout()
        f.setSpacing(10)
        self.ol_client = QLineEdit()
        self.ol_client.setPlaceholderText("UUID клиента...")
        f.addRow("Клиент ID:", self.ol_client)
        self.ol_provider = QComboBox()
        self.ol_provider.addItems(["TTLock", "KERONG Cloud", "Sciener"])
        f.addRow("Провайдер:", self.ol_provider)
        self.ol_lock_id = QLineEdit()
        self.ol_lock_id.setPlaceholderText("ID замка в облаке...")
        f.addRow("Lock ID:", self.ol_lock_id)
        self.ol_pass = QLineEdit()
        self.ol_pass.setPlaceholderText("Временный пароль (TTLock)...")
        f.addRow("Пароль:", self.ol_pass)
        lay.addLayout(f)
        b = QPushButton("💾  Создать цифровой ключ")
        b.setStyleSheet(BTN_SUCCESS)
        b.setMinimumHeight(44)
        b.clicked.connect(self._create_online_key)
        lay.addWidget(b)
        self.ol_log = QPlainTextEdit()
        self.ol_log.setMaximumBlockCount(100)
        self.ol_log.setPlaceholderText("Журнал онлайн-замков...")
        lay.addWidget(self.ol_log, 1)
        return w

    def _create_online_key(self):
        cid = self.ol_client.text().strip()
        if not cid:
            QMessageBox.warning(self, "Клиент", "Введите ID клиента")
            return
        payload = {
            "client_id": cid,
            "lock_provider": self.ol_provider.currentText().lower().replace(" ", "-"),
            "lock_id": self.ol_lock_id.text().strip() or "auto",
            "password": self.ol_pass.text().strip() or None,
            "valid_until": None
        }
        r = self._req("POST", "/credentials/online-lock", payload)
        if isinstance(r, dict) and "_err" not in r:
            self.ol_log.appendPlainText("✅ Ключ создан: " + payload["lock_provider"] + " / " + payload["lock_id"])
        else:
            self.ol_log.appendPlainText("❌ Ошибка: " + str(r.get("_body", str(r))))