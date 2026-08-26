"""E18: Коммерция — white-label и тенанты (UI)."""
import json
import urllib.request
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
                             QLineEdit, QPushButton, QCheckBox, QTableWidget,
                             QTableWidgetItem, QComboBox, QSpinBox, QMessageBox, QFormLayout)


def _base():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        return cfg.get("api_base") or cfg.get("base_url") or "http://localhost:8001/api/v1"
    except Exception:
        return "http://localhost:8001/api/v1"


def _req(method, path, data=None):
    r = urllib.request.Request(_base() + path,
                               data=json.dumps(data).encode() if data is not None else None,
                               headers={"Content-Type": "application/json"}, method=method)
    return json.load(urllib.request.urlopen(r, timeout=10))


class CommerceTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(self._brand_tab(), "🎨 White-label")
        tabs.addTab(self._tenants_tab(), "🏢 Тенанты")
        lay.addWidget(tabs)

    def _brand_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.f = {}
        for key, label in [("club_name", "Название клуба"), ("tagline", "Слоган"),
                           ("logo_url", "URL логотипа"), ("primary_color", "Основной цвет"),
                           ("accent_color", "Акцентный цвет"), ("support_email", "Email поддержки"),
                           ("support_phone", "Телефон поддержки"), ("custom_domain", "Свой домен")]:
            e = QLineEdit()
            self.f[key] = e
            form.addRow(label + ":", e)
        lay.addLayout(form)
        self.cb_powered = QCheckBox("Показывать «Powered by FitIntel»")
        lay.addWidget(self.cb_powered)
        btns = QHBoxLayout()
        b_load = QPushButton("🔄 Загрузить")
        b_load.clicked.connect(self.load_brand)
        b_save = QPushButton("💾 Сохранить")
        b_save.clicked.connect(self.save_brand)
        btns.addWidget(b_load)
        btns.addWidget(b_save)
        lay.addLayout(btns)
        self.brand_status = QLabel("")
        lay.addWidget(self.brand_status)
        lay.addStretch(1)
        self.load_brand()
        return w

    def load_brand(self):
        try:
            r = _req("GET", "/brand/settings")
            for k, e in self.f.items():
                e.setText(str(r.get(k) or ""))
            self.cb_powered.setChecked(bool(r.get("powered_by", True)))
            self.brand_status.setText("Загружено")
        except Exception as e:
            self.brand_status.setText("Ошибка загрузки: " + str(e)[:120])

    def save_brand(self):
        try:
            data = {k: e.text().strip() for k, e in self.f.items()}
            data["powered_by"] = self.cb_powered.isChecked()
            _req("POST", "/brand/settings", data)
            self.brand_status.setText("✅ Сохранено")
        except Exception as e:
            self.brand_status.setText("❌ " + str(e)[:150])

    def _tenants_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(["ID", "Код", "Название", "Тариф", "Лимит", "Email", "Активен"])
        lay.addWidget(self.tbl)
        form = QHBoxLayout()
        self.e_code = QLineEdit(); self.e_code.setPlaceholderText("Код (club2)")
        self.e_name = QLineEdit(); self.e_name.setPlaceholderText("Название клуба")
        self.cb_plan = QComboBox(); self.cb_plan.addItems(["Freemium", "Pro", "Enterprise"])
        self.sp_max = QSpinBox(); self.sp_max.setRange(1, 1000000); self.sp_max.setValue(300)
        self.e_mail = QLineEdit(); self.e_mail.setPlaceholderText("Email контакта")
        for x in (self.e_code, self.e_name, self.cb_plan, self.sp_max, self.e_mail):
            form.addWidget(x)
        lay.addLayout(form)
        btns = QHBoxLayout()
        b_add = QPushButton("➕ Добавить тенанта"); b_add.clicked.connect(self.add_tenant)
        b_tgl = QPushButton("🔁 Вкл/Выкл выбранный"); b_tgl.clicked.connect(self.toggle_tenant)
        b_ref = QPushButton("🔄 Обновить"); b_ref.clicked.connect(self.load_tenants)
        for b in (b_add, b_tgl, b_ref):
            btns.addWidget(b)
        lay.addLayout(btns)
        self.load_tenants()
        return w

    def load_tenants(self):
        try:
            rows = _req("GET", "/brand/tenants")
            self.tbl.setRowCount(0)
            for t in rows:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)
                vals = [t.get("id"), t.get("code"), t.get("name"), t.get("plan"),
                        t.get("max_clients"), t.get("contact_email"),
                        "✅" if t.get("active") else "⛔"]
                for i, v in enumerate(vals):
                    self.tbl.setItem(r, i, QTableWidgetItem(str(v if v is not None else "")))
        except Exception as e:
            print("[E18] tenants:", str(e)[:120])

    def add_tenant(self):
        try:
            _req("POST", "/brand/tenants", {
                "code": self.e_code.text().strip(),
                "name": self.e_name.text().strip(),
                "plan": self.cb_plan.currentText(),
                "max_clients": self.sp_max.value(),
                "contact_email": self.e_mail.text().strip()})
            self.load_tenants()
        except Exception as e:
            QMessageBox.warning(self, "Тенант", str(e)[:200])

    def toggle_tenant(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        tid = self.tbl.item(row, 0).text()
        try:
            _req("POST", f"/brand/tenants/{tid}/toggle")
            self.load_tenants()
        except Exception as e:
            QMessageBox.warning(self, "Тенант", str(e)[:200])
