"""E19: Экспорт данных + 152-ФЗ право на забвение (UI)."""
import json
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
                             QLineEdit, QPushButton, QComboBox, QTableWidget,
                             QTableWidgetItem, QMessageBox, QFileDialog)

ENTITIES = ["clients", "payments", "visits", "subscriptions", "tariffs", "users", "tenants", "notification_log"]


def _base():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        return cfg.get("api_base") or cfg.get("base_url") or "http://localhost:8001/api/v1"
    except Exception:
        return "http://localhost:8001/api/v1"


def _token():
    try:
        cfg = json.load(open("client_settings.json", encoding="utf-8"))
        r = urllib.request.Request(_base() + "/auth/login",
            data=json.dumps({"login": cfg.get("saved_login"), "password": cfg.get("saved_password")}).encode(),
            headers={"Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(r, timeout=10))
        return d.get("access_token") or d.get("token")
    except Exception:
        return None


def _get(path):
    req = urllib.request.Request(_base() + path)
    tok = _token()
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    return urllib.request.urlopen(req, timeout=30)


class ExportTab(QWidget):
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(self._export_tab(), "📥 Экспорт")
        tabs.addTab(self._forget_tab(), "🗑 Право на забвение")
        tabs.addTab(self._log_tab(), "📋 Журнал")
        lay.addWidget(tabs)

    def _export_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Выберите данные и формат — файл сохранится на диск."))
        row = QHBoxLayout()
        self.cb_entity = QComboBox()
        self.cb_entity.addItems(ENTITIES)
        self.cb_fmt = QComboBox()
        self.cb_fmt.addItems(["xlsx", "json"])
        b = QPushButton("📥 Скачать")
        b.clicked.connect(self.do_export)
        row.addWidget(QLabel("Данные:"))
        row.addWidget(self.cb_entity)
        row.addWidget(QLabel("Формат:"))
        row.addWidget(self.cb_fmt)
        row.addWidget(b)
        lay.addLayout(row)
        self.exp_status = QLabel("")
        lay.addWidget(self.exp_status)
        lay.addStretch(1)
        return w

    def do_export(self):
        ent = self.cb_entity.currentText()
        fmt = self.cb_fmt.currentText()
        tok = _token()
        if not tok:
            self.exp_status.setText("❌ Нет токена (проверьте saved_login в client_settings.json)")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить экспорт", f"{ent}.{fmt}",
                                              "Excel (*.xlsx)" if fmt == "xlsx" else "JSON (*.json)")
        if not path:
            return
        try:
            req = urllib.request.Request(_base() + f"/export/{ent}?fmt={fmt}&token={tok}")
            data = urllib.request.urlopen(req, timeout=60).read()
            with open(path, "wb") as f:
                f.write(data)
            self.exp_status.setText(f"✅ Сохранено: {path} ({len(data)} байт)")
        except Exception as e:
            self.exp_status.setText("❌ " + str(e)[:200])

    def _forget_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("152-ФЗ «О персональных данных»: анонимизация клиента по его ID.\n"
                             "ФИО, телефон, email и дата рождения будут заменены на «***». Действие необратимо!"))
        self.e_cid = QLineEdit()
        self.e_cid.setPlaceholderText("ID клиента (из вкладки Клиенты)")
        self.e_reason = QLineEdit("запрос субъекта (152-ФЗ)")
        lay.addWidget(self.e_cid)
        lay.addWidget(self.e_reason)
        b = QPushButton("🗑 Анонимизировать клиента")
        b.clicked.connect(self.do_forget)
        lay.addWidget(b)
        self.frg_status = QLabel("")
        lay.addWidget(self.frg_status)
        lay.addStretch(1)
        return w

    def do_forget(self):
        cid = self.e_cid.text().strip()
        if not cid:
            self.frg_status.setText("Введите ID клиента")
            return
        if QMessageBox.question(self, "152-ФЗ",
                f"Анонимизировать клиента {cid}?\nПерсональные данные будут стёрты безвозвратно!") != QMessageBox.StandardButton.Yes:
            return
        tok = _token()
        try:
            req = urllib.request.Request(_base() + f"/export/forget?token={tok}",
                data=json.dumps({"client_id": cid, "reason": self.e_reason.text().strip()}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            r = json.load(urllib.request.urlopen(req, timeout=15))
            self.frg_status.setText(f"✅ Анонимизировано полей: {len(r.get('anonymized', []))}")
        except urllib.error.HTTPError as e:
            self.frg_status.setText(f"❌ {e.code}: {e.read().decode()[:150]}")
        except Exception as e:
            self.frg_status.setText("❌ " + str(e)[:150])

    def _log_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["ID", "Действие", "Данные", "Формат", "Время"])
        lay.addWidget(self.tbl)
        b = QPushButton("🔄 Обновить")
        b.clicked.connect(self.load_log)
        lay.addWidget(b)
        self.load_log()
        return w

    def load_log(self):
        try:
            tok = _token()
            rows = json.loads(_get(f"/export/log/list?token={tok}").read())
            self.tbl.setRowCount(0)
            for t in rows:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)
                for i, k in enumerate(("id", "action", "entity", "fmt", "created_at")):
                    self.tbl.setItem(r, i, QTableWidgetItem(str(t.get(k, ""))))
        except Exception as e:
            print("[E19] log:", str(e)[:120])
