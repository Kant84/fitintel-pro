"""E21+E22: Интеграции — A&A и 1С Fitness."""
import json, urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QPlainTextEdit, QTabWidget, QLineEdit, QFormLayout, QComboBox)
from PyQt6.QtCore import Qt


class IntegrationsTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(self._aa_tab(), " A&A")
        tabs.addTab(self._1c_tab(), " 1С Fitness")
        tabs.addTab(self._connectors_tab(), " Внешние системы")
        lay.addWidget(tabs)

    # === BASE / TOKEN ===
    def _base(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            return cfg.get("api_base") or "http://192.168.101.182/api/v1"
        except Exception:
            return "http://192.168.101.182/api/v1"

    def _token(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            try:
                from secure_store import get_token as _gt
                _t = _gt() or cfg.get("token")
                if _t:
                    return _t
            except Exception:
                pass
            r = urllib.request.Request(self._base() + "/auth/login",
                data=json.dumps({"login": cfg.get("saved_login"), "password": cfg.get("saved_password")}).encode(),
                headers={"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(r, timeout=10)).get("access_token")
        except Exception:
            return None

    def _req(self, method, path, data=None):
        tok = self._token()
        r = urllib.request.Request(self._base() + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method)
        if tok:
            r.add_header("Authorization", "Bearer " + tok)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return json.load(opener.open(r, timeout=15))

    # === A&A ===
    def _aa_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        sub = QTabWidget()
        sub.setMovable(True)
        sub.addTab(self._aa_import(), " Импорт CSV")
        sub.addTab(self._aa_export(), " Экспорт")
        sub.addTab(self._aa_log(), " Журнал")
        sub.addTab(self._aa_webhook(), " Webhook")
        lay.addWidget(sub)
        return w

    def _aa_import(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Импорт клиентов из A&A</h3>"))
        lay.addWidget(QLabel("Ожидаемые колонки CSV (разделитель ;):<br>"
            "<code>ФИО;Телефон;Email;Дата рождения;Пол;Категория;Статус;Фото(URL)</code>"))
        h = QHBoxLayout()
        self.aa_csv_path = QLineEdit()
        self.aa_csv_path.setPlaceholderText("Путь к CSV-файлу...")
        h.addWidget(self.aa_csv_path)
        b = QPushButton(" Обзор")
        b.clicked.connect(self._aa_browse)
        h.addWidget(b)
        lay.addLayout(h)
        b_imp = QPushButton(" Импортировать")
        b_imp.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_imp.clicked.connect(self._aa_do_import)
        lay.addWidget(b_imp)
        self.aa_imp_status = QLabel("")
        lay.addWidget(self.aa_imp_status)
        lay.addStretch(1)
        return w

    def _aa_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV из A&A", "", "CSV (*.csv)")
        if path:
            self.aa_csv_path.setText(path)

    def _aa_do_import(self):
        path = self.aa_csv_path.text()
        if not path:
            QMessageBox.warning(self, "Файл", "Выберите CSV-файл")
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                csv_text = f.read()
            r = self._req("POST", "/aa/import-csv", {"csv": csv_text, "entity": "clients"})
            self.aa_imp_status.setText(f" Импортировано: {r.get('imported', 0)}, ошибок: {r.get('errors', 0)}")
        except Exception as e:
            self.aa_imp_status.setText(" " + str(e)[:200])

    def _aa_export(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Экспорт клиентов для A&A</h3>"))
        h = QHBoxLayout()
        b_json = QPushButton(" JSON")
        b_json.clicked.connect(self._aa_do_export_json)
        h.addWidget(b_json)
        b_csv = QPushButton(" CSV")
        b_csv.clicked.connect(self._aa_do_export_csv)
        h.addWidget(b_csv)
        lay.addLayout(h)
        self.aa_exp_tbl = QTableWidget(0, 6)
        self.aa_exp_tbl.setHorizontalHeaderLabels(["Фамилия", "Имя", "Телефон", "Email", "Категория", "Фото"])
        self.aa_exp_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.aa_exp_tbl)
        return w

    def _aa_do_export_json(self):
        try:
            r = self._req("GET", "/aa/export?entity=clients&format=json")
            rows = r.get("data", [])
            self.aa_exp_tbl.setRowCount(len(rows))
            for i, c in enumerate(rows):
                self.aa_exp_tbl.setItem(i, 0, QTableWidgetItem(str(c.get("last_name", ""))))
                self.aa_exp_tbl.setItem(i, 1, QTableWidgetItem(str(c.get("first_name", ""))))
                self.aa_exp_tbl.setItem(i, 2, QTableWidgetItem(str(c.get("phone", ""))))
                self.aa_exp_tbl.setItem(i, 3, QTableWidgetItem(str(c.get("email", ""))))
                self.aa_exp_tbl.setItem(i, 4, QTableWidgetItem(str(c.get("client_category", ""))))
                self.aa_exp_tbl.setItem(i, 5, QTableWidgetItem(str(c.get("photo_url", ""))[:30]))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _aa_do_export_csv(self):
        try:
            r = self._req("GET", "/aa/export?entity=clients&format=csv")
            csv_data = r.get("csv", "")
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", "aa_export.csv", "CSV (*.csv)")
            if path:
                with open(path, "w", encoding="utf-8-sig") as f:
                    f.write(csv_data)
                QMessageBox.information(self, "CSV", f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _aa_log(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        b = QPushButton(" Обновить журнал")
        b.clicked.connect(self._aa_load_log)
        lay.addWidget(b)
        self.aa_log_tbl = QTableWidget(0, 5)
        self.aa_log_tbl.setHorizontalHeaderLabels(["Время", "Направление", "Сущность", "Кол-во", "Статус"])
        self.aa_log_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.aa_log_tbl)
        return w

    def _aa_load_log(self):
        try:
            r = self._req("GET", "/aa/sync-log")
            self.aa_log_tbl.setRowCount(len(r))
            for i, row in enumerate(r[:50]):
                self.aa_log_tbl.setItem(i, 0, QTableWidgetItem(str(row.get("created_at", ""))[:19]))
                self.aa_log_tbl.setItem(i, 1, QTableWidgetItem(str(row.get("direction", ""))))
                self.aa_log_tbl.setItem(i, 2, QTableWidgetItem(str(row.get("entity", ""))))
                self.aa_log_tbl.setItem(i, 3, QTableWidgetItem(str(row.get("records_count", ""))))
                self.aa_log_tbl.setItem(i, 4, QTableWidgetItem(str(row.get("status", ""))))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _aa_webhook(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Webhook для A&A</h3>"))
        lay.addWidget(QLabel("URL для настройки в A&A (исходящий webhook):"))
        url = f"{self._base()}/aa/webhook"
        le = QLineEdit(url)
        le.setReadOnly(True)
        lay.addWidget(le)
        lay.addWidget(QLabel("Формат JSON:"))
        te = QPlainTextEdit()
        te.setReadOnly(True)
        te.setPlainText('{\n  "clients": [\n    {"first_name":"Иван","last_name":"Иванов","phone":"+7916...", "photo_url":"https://..."}\n  ]\n}')
        lay.addWidget(te)
        lay.addStretch(1)
        return w

    # === 1С Fitness ===
    def _1c_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        sub = QTabWidget()
        sub.setMovable(True)
        sub.addTab(self._1c_export(), " Экспорт в 1С")
        sub.addTab(self._1c_import(), " Импорт из 1С")
        sub.addTab(self._1c_settings(), " Подключение и синхронизация")
        lay.addWidget(sub)
        return w

    def _1c_export(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Экспорт в 1С Fitness / 1С:Бухгалтерия</h3>"))
        lay.addWidget(QLabel("Формат: CommerceML 2.0 (XML)"))
        f = QFormLayout()
        self._1c_period = QComboBox()
        self._1c_period.addItems(["2026-08", "2026-07", "2026-06"])
        f.addRow("Период:", self._1c_period)
        self._1c_type = QComboBox()
        self._1c_type.addItems(["Номенклатура", "Контрагенты", "Проводки (ОСВ)"])
        f.addRow("Тип:", self._1c_type)
        lay.addLayout(f)
        b_exp = QPushButton(" Сгенерировать XML")
        b_exp.setStyleSheet("QPushButton { background: #3B82F6; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_exp.clicked.connect(self._1c_do_export)
        lay.addWidget(b_exp)
        self._1c_status = QLabel("")
        lay.addWidget(self._1c_status)
        lay.addStretch(1)
        return w

    def _1c_do_export(self):
        try:
            period = self._1c_period.currentText()
            typ = self._1c_type.currentText()
            # Пока mock — сохраняем заглушку
            xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<CommerceML>\n  <period>{period}</period>\n  <type>{typ}</type>\n  <!-- mock -->\n</CommerceML>'
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить XML", f"1c_export_{period}.xml", "XML (*.xml)")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(xml)
                self._1c_status.setText(f" Сохранено: {path}")
        except Exception as e:
            self._1c_status.setText(" " + str(e)[:200])

    def _1c_import(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Импорт из 1С</h3>"))
        lay.addWidget(QLabel("Загрузка номенклатуры / контрагентов из 1С (XML/CSV):"))
        h = QHBoxLayout()
        self._1c_imp_path = QLineEdit()
        self._1c_imp_path.setPlaceholderText("Путь к файлу 1С...")
        h.addWidget(self._1c_imp_path)
        b = QPushButton(" Обзор")
        b.clicked.connect(lambda: self._1c_imp_path.setText(QFileDialog.getOpenFileName(self, "Файл 1С", "", "XML/CSV (*.xml *.csv)")[0]))
        h.addWidget(b)
        lay.addLayout(h)
        b_imp = QPushButton(" Импортировать")
        b_imp.clicked.connect(lambda: QMessageBox.information(self, "1С", "Импорт из 1С — в разработке (mock)"))
        lay.addWidget(b_imp)
        lay.addStretch(1)
        return w

    def _1c_load_cfg(self) -> dict:
        from paths import SETTINGS
        try:
            cfg = json.load(open(SETTINGS, encoding="utf-8"))
        except Exception:
            cfg = {}
        return cfg.get("integrations", {}).get("fitness1c", {}) or {}

    def _1c_save_cfg(self):
        from paths import SETTINGS
        try:
            cfg = json.load(open(SETTINGS, encoding="utf-8"))
        except Exception:
            cfg = {}
        cfg.setdefault("integrations", {})["fitness1c"] = {
            "base_url": self._1c_url.text().strip(),
            "username": self._1c_user.text().strip(),
            "password": self._1c_pass.text(),
            "api_key": self._1c_key.text().strip(),
            "club_id": self._1c_club.text().strip(),
        }
        json.dump(cfg, open(SETTINGS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def _1c_client(self):
        from integrations.fitness1c import Fitness1CClient, Fitness1CConfig
        cfg = {k: v for k, v in self._1c_load_cfg().items()
               if k in ("base_url", "username", "password", "api_key", "club_id", "timeout")}
        return Fitness1CClient(Fitness1CConfig(**cfg))

    def _1c_do_test(self):
        try:
            self._1c_save_cfg()
            info = self._1c_client().test_connection()
            club = info["clubs"][0]
            self._1c_status.setStyleSheet("color: #10b981; font-weight: 600;")
            self._1c_status.setText(f" OK: {club['name']} (club_id={info['club_id']})")
        except Exception as e:
            self._1c_status.setStyleSheet("color: #ef4444; font-weight: 600;")
            self._1c_status.setText(" Ошибка: " + str(e)[:220])

    def _1c_do_sync(self):
        try:
            self._1c_save_cfg()
            client = self._1c_client()
            customers = client.list_customers()
            lines = ["ФИО;Телефон;Email;Дата рождения;Пол;Категория;Статус;Фото(URL)"]
            for c in customers:
                ms = client.list_memberships(c["id"])
                status, cat = "Активен", ""
                if ms:
                    m0 = ms[0]
                    cat = m0.get("name", "")
                    if not m0.get("is_active"):
                        status = "Истёк"
                    elif m0.get("freezes"):
                        status = "Заморожен"
                photo = f"{client.config.base_url.rstrip('/')}/customers/{c['id']}/photo/"

                def esc(v):
                    return str(v or "").replace(";", ",").replace("\n", " ")

                lines.append(";".join([
                    esc(c.get("name")), esc(c.get("phone")), esc(c.get("email")),
                    esc(c.get("birthday")), esc(c.get("sex")), esc(cat), status, photo,
                ]))
            self._1c_status.setText(f" 1С: клиентов получено {len(customers)}. Отправка в FitIntel: {self._base()}/aa/import-csv ...")
            from PyQt6.QtWidgets import QApplication; QApplication.processEvents()
            r = self._req("POST", "/aa/import-csv", {"csv": "\n".join(lines), "entity": "clients"})
            self._1c_status.setStyleSheet("color: #10b981; font-weight: 600;")
            self._1c_status.setText(
                f" Синхронизировано: {r.get('imported', 0)}, ошибок: {r.get('errors', 0)} (из 1С: {len(customers)})")
        except Exception as e:
            self._1c_status.setStyleSheet("color: #ef4444; font-weight: 600;")
            self._1c_status.setText(f" Ошибка синхронизации [бэкенд: {self._base()}]: " + str(e)[:200])

    def _1c_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Подключение к 1С:Фитнес клуб (API V3)</h3>"))
        cfg = self._1c_load_cfg()
        f = QFormLayout()
        self._1c_url = QLineEdit(cfg.get("base_url", ""))
        self._1c_url.setPlaceholderText("http://192.168.101.50:8095/hs/api/v3")
        f.addRow("URL API V3:", self._1c_url)
        self._1c_user = QLineEdit(cfg.get("username", ""))
        self._1c_user.setPlaceholderText("Имя для входа пользователя ИБ")
        f.addRow("Пользователь:", self._1c_user)
        self._1c_pass = QLineEdit(cfg.get("password", ""))
        self._1c_pass.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("Пароль:", self._1c_pass)
        self._1c_key = QLineEdit(cfg.get("api_key", ""))
        self._1c_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._1c_key.setPlaceholderText("ключ приложения (Настройки API в 1С)")
        f.addRow("Ключ (apikey):", self._1c_key)
        self._1c_club = QLineEdit(cfg.get("club_id", ""))
        self._1c_club.setPlaceholderText("пусто = первый клуб из /clubs/")
        f.addRow("Club ID:", self._1c_club)
        lay.addLayout(f)
        h = QHBoxLayout()
        b_save = QPushButton(" Сохранить")
        b_save.clicked.connect(self._1c_save_cfg)
        b_test = QPushButton(" Тест связи")
        b_test.setStyleSheet("QPushButton { background: #3B82F6; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; }")
        b_test.clicked.connect(self._1c_do_test)
        b_sync = QPushButton(" Синхронизировать клиентов")
        b_sync.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: 600; }")
        b_sync.clicked.connect(self._1c_do_sync)
        h.addWidget(b_save)
        h.addWidget(b_test)
        h.addWidget(b_sync)
        h.addStretch(1)
        lay.addLayout(h)
        self._1c_status = QLabel("Укажите параметры и нажмите «Тест связи»")
        self._1c_status.setWordWrap(True)
        lay.addWidget(self._1c_status)
        lay.addWidget(QLabel(" Пароль и ключ хранятся в client_settings.json (шифрование — в roadmap C1–C4)"))
        lay.addStretch(1)
        return w
    def _connectors_tab(self):
        from windows.connectors_tab import ConnectorsTab
        return ConnectorsTab(self.api, self)

# === авто-refresh токена при 401 (паритет с E70 для urllib-вызовов) ===
try:
    import json as _json
    import urllib.request as _uq
    import urllib.error as _ue
    from paths import SETTINGS as _SETTINGS
    import inspect as _i

    def _refresh_settings_token():
        try:
            cfg = _json.load(open(_SETTINGS, encoding="utf-8"))
            rt = None
            try:
                from secure_store import get_refresh_token as _grt
                rt = _grt()
            except Exception:
                rt = None
            if not rt:
                rt = cfg.get("refresh_token")
            if not rt:
                return None
            req = _uq.Request(cfg["api_base"] + "/auth/refresh",
                              data=_json.dumps({"refresh_token": rt}).encode(),
                              headers={"Content-Type": "application/json"})
            resp = _json.load(_uq.urlopen(req, timeout=10))
            from secure_store import save_tokens as _st
            _st(access=resp["access_token"], refresh=resp.get("refresh_token"))
            return cfg["token"]
        except Exception:
            return None

    for _n, _o in list(globals().items()):
        if (_i.isclass(_o) and hasattr(_o, "_req")
                and getattr(_o, "__module__", "") == __name__):
            _orig_req = _o._req
            def _mk_req(orig):
                def _req(self, method, path, data=None):
                    try:
                        return orig(self, method, path, data)
                    except _ue.HTTPError as e:
                        if e.code != 401:
                            raise
                        tok = _refresh_settings_token()
                        if not tok:
                            raise
                        try:
                            self.api.set_token(tok)
                        except Exception:
                            pass
                        return orig(self, method, path, data)
                return _req
            _o._req = _mk_req(_orig_req)
            print("401-refresh OK:", __name__)
            break
except Exception as _e:
    print("401-refresh FAIL:", _e)