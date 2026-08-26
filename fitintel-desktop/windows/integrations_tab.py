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
        tabs.addTab(self._aa_tab(), "🔗 A&A")
        tabs.addTab(self._1c_tab(), "🔄 1С Fitness")
        lay.addWidget(tabs)

    # === BASE / TOKEN ===
    def _base(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
            return cfg.get("api_base") or "http://localhost:8001/api/v1"
        except Exception:
            return "http://localhost:8001/api/v1"

    def _token(self):
        try:
            cfg = json.load(open("client_settings.json", encoding="utf-8"))
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
        return json.load(urllib.request.urlopen(r, timeout=15))

    # === A&A ===
    def _aa_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        sub = QTabWidget()
        sub.setMovable(True)
        sub.addTab(self._aa_import(), "📥 Импорт CSV")
        sub.addTab(self._aa_export(), "📤 Экспорт")
        sub.addTab(self._aa_log(), "📝 Журнал")
        sub.addTab(self._aa_webhook(), "🔗 Webhook")
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
        b = QPushButton("📂 Обзор")
        b.clicked.connect(self._aa_browse)
        h.addWidget(b)
        lay.addLayout(h)
        b_imp = QPushButton("📥 Импортировать")
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
            self.aa_imp_status.setText(f"✅ Импортировано: {r.get('imported', 0)}, ошибок: {r.get('errors', 0)}")
        except Exception as e:
            self.aa_imp_status.setText("❌ " + str(e)[:200])

    def _aa_export(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Экспорт клиентов для A&A</h3>"))
        h = QHBoxLayout()
        b_json = QPushButton("📤 JSON")
        b_json.clicked.connect(self._aa_do_export_json)
        h.addWidget(b_json)
        b_csv = QPushButton("📄 CSV")
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
        b = QPushButton("🔄 Обновить журнал")
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
        sub.addTab(self._1c_export(), "📤 Экспорт в 1С")
        sub.addTab(self._1c_import(), "📥 Импорт из 1С")
        sub.addTab(self._1c_settings(), "⚙️ Настройки")
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
        b_exp = QPushButton("📤 Сгенерировать XML")
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
                self._1c_status.setText(f"✅ Сохранено: {path}")
        except Exception as e:
            self._1c_status.setText("❌ " + str(e)[:200])

    def _1c_import(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Импорт из 1С</h3>"))
        lay.addWidget(QLabel("Загрузка номенклатуры / контрагентов из 1С (XML/CSV):"))
        h = QHBoxLayout()
        self._1c_imp_path = QLineEdit()
        self._1c_imp_path.setPlaceholderText("Путь к файлу 1С...")
        h.addWidget(self._1c_imp_path)
        b = QPushButton("📂 Обзор")
        b.clicked.connect(lambda: self._1c_imp_path.setText(QFileDialog.getOpenFileName(self, "Файл 1С", "", "XML/CSV (*.xml *.csv)")[0]))
        h.addWidget(b)
        lay.addLayout(h)
        b_imp = QPushButton("📥 Импортировать")
        b_imp.clicked.connect(lambda: QMessageBox.information(self, "1С", "Импорт из 1С — в разработке (mock)"))
        lay.addWidget(b_imp)
        lay.addStretch(1)
        return w

    def _1c_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("<h3>Настройки подключения к 1С</h3>"))
        f = QFormLayout()
        self._1c_url = QLineEdit("http://1c-server:8080/base")
        f.addRow("URL 1С:", self._1c_url)
        self._1c_user = QLineEdit("Администратор")
        f.addRow("Пользователь:", self._1c_user)
        self._1c_pass = QLineEdit()
        self._1c_pass.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow("Пароль:", self._1c_pass)
        lay.addLayout(f)
        b_save = QPushButton("💾 Сохранить настройки")
        b_save.clicked.connect(lambda: QMessageBox.information(self, "1С", "Настройки сохранены (локально)"))
        lay.addWidget(b_save)
        lay.addWidget(QLabel("⚠️ Режим mock — реальное подключение требует настройки на стороне 1С"))
        lay.addStretch(1)
        return w
