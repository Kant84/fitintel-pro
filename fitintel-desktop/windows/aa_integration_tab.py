"""E21: Интеграция с A&A — импорт/экспорт CSV, webhook, журнал."""
import json, urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QPlainTextEdit, QTabWidget, QLineEdit)
from PyQt6.QtCore import Qt


class AAIntegrationTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(self._import_tab(), "📥 Импорт из A&A")
        tabs.addTab(self._export_tab(), "📤 Экспорт в A&A")
        tabs.addTab(self._log_tab(), "📝 Журнал")
        tabs.addTab(self._webhook_tab(), "🔗 Webhook")
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

    def _import_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Импорт клиентов из A&A через CSV"))
        lay.addWidget(QLabel("Ожидаемые колонки: ФИО;Телефон;Email;Дата рождения;Пол;Категория;Статус;Фото(URL)"))
        h = QHBoxLayout()
        self.csv_path = QLineEdit()
        self.csv_path.setPlaceholderText("Путь к CSV-файлу...")
        h.addWidget(self.csv_path)
        b_browse = QPushButton("📂 Обзор")
        b_browse.clicked.connect(self._browse_csv)
        h.addWidget(b_browse)
        lay.addLayout(h)
        b_import = QPushButton("📥 Импортировать")
        b_import.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }")
        b_import.clicked.connect(self._do_import)
        lay.addWidget(b_import)
        self.imp_status = QLabel("")
        lay.addWidget(self.imp_status)
        lay.addStretch(1)
        return w

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите CSV из A&A", "", "CSV (*.csv)")
        if path:
            self.csv_path.setText(path)

    def _do_import(self):
        path = self.csv_path.text()
        if not path:
            QMessageBox.warning(self, "Файл", "Выберите CSV-файл")
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                csv_text = f.read()
            r = self._req("POST", "/aa/import-csv", {"csv": csv_text, "entity": "clients"})
            self.imp_status.setText(f"✅ Импортировано: {r.get('imported', 0)}, ошибок: {r.get('errors', 0)}")
        except Exception as e:
            self.imp_status.setText("❌ " + str(e)[:200])

    def _export_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Экспорт клиентов для A&A"))
        b_exp = QPushButton("📤 Экспорт JSON")
        b_exp.clicked.connect(self._do_export)
        lay.addWidget(b_exp)
        b_csv = QPushButton("📄 Экспорт CSV")
        b_csv.clicked.connect(self._do_export_csv)
        lay.addWidget(b_csv)
        self.exp_tbl = QTableWidget(0, 5)
        self.exp_tbl.setHorizontalHeaderLabels(["Фамилия", "Имя", "Телефон", "Email", "Категория"])
        self.exp_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.exp_tbl)
        return w

    def _do_export(self):
        try:
            r = self._req("GET", "/aa/export?entity=clients&format=json")
            rows = r.get("data", [])
            self.exp_tbl.setRowCount(len(rows))
            for i, c in enumerate(rows):
                self.exp_tbl.setItem(i, 0, QTableWidgetItem(str(c.get("last_name", ""))))
                self.exp_tbl.setItem(i, 1, QTableWidgetItem(str(c.get("first_name", ""))))
                self.exp_tbl.setItem(i, 2, QTableWidgetItem(str(c.get("phone", ""))))
                self.exp_tbl.setItem(i, 3, QTableWidgetItem(str(c.get("email", ""))))
                self.exp_tbl.setItem(i, 4, QTableWidgetItem(str(c.get("client_category", ""))))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _do_export_csv(self):
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

    def _log_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        b = QPushButton("🔄 Обновить журнал")
        b.clicked.connect(self._load_log)
        lay.addWidget(b)
        self.log_tbl = QTableWidget(0, 5)
        self.log_tbl.setHorizontalHeaderLabels(["Время", "Направление", "Сущность", "Кол-во", "Статус"])
        self.log_tbl.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.log_tbl)
        return w

    def _load_log(self):
        try:
            r = self._req("GET", "/aa/sync-log")
            self.log_tbl.setRowCount(len(r))
            for i, row in enumerate(r[:50]):
                self.log_tbl.setItem(i, 0, QTableWidgetItem(str(row.get("created_at", ""))[:19]))
                self.log_tbl.setItem(i, 1, QTableWidgetItem(str(row.get("direction", ""))))
                self.log_tbl.setItem(i, 2, QTableWidgetItem(str(row.get("entity", ""))))
                self.log_tbl.setItem(i, 3, QTableWidgetItem(str(row.get("records_count", ""))))
                self.log_tbl.setItem(i, 4, QTableWidgetItem(str(row.get("status", ""))))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)[:200])

    def _webhook_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Webhook URL для A&A:"))
        url = f"{self._base()}/aa/webhook"
        le = QLineEdit(url)
        le.setReadOnly(True)
        lay.addWidget(le)
        lay.addWidget(QLabel("Отправьте POST с JSON: {\"clients\": [{\"first_name\":\"...\",\"phone\":\"...\",...}]}"))
        self.webhook_resp = QPlainTextEdit()
        self.webhook_resp.setReadOnly(True)
        self.webhook_resp.setPlaceholderText("Ответ webhook...")
        lay.addWidget(self.webhook_resp)
        lay.addStretch(1)
        return w
