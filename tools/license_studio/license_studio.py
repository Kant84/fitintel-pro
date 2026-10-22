# -*- coding: utf-8 -*-
"""FitIntel License Studio — генератор лицензий (только для владельца).
Ed25519: приватный ключ ТОЛЬКО у владельца (license_private.key, НЕ коммитить!).
Формат ключа БЕЗ дефисов: FIPRO-<raw>.<sig> (дефис конфликтовал с base64url).
Пароль клиента ВНУТРИ подписанного ключа — клиент входит ровно по нему."""
import os, sys, json, base64, secrets, csv, string
from datetime import date, datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSpinBox, QDateEdit, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QFileDialog)
from PyQt6.QtCore import QDate
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

DIR = os.path.dirname(os.path.abspath(__file__))
PRIV_FILE = os.path.join(DIR, "license_private.key")   # ТОЛЬКО у владельца! В git НЕ коммитить!
PUB_FILE  = os.path.join(DIR, "license_public.key")    # копия → репо: app/core/license_public.pem
REG_FILE = os.path.join(DIR, "licenses_issued.json")
PLANS = ["Freemium", "Lite", "Start", "Pro", "Enterprise"]


def load_keys():
    """Загружает или создаёт пару Ed25519. Приватный — только локально."""
    if os.path.exists(PRIV_FILE):
        priv = serialization.load_pem_private_key(open(PRIV_FILE, "rb").read(), password=None)
    else:
        priv = Ed25519PrivateKey.generate()
        open(PRIV_FILE, "wb").write(priv.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        open(PUB_FILE, "wb").write(priv.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return priv


def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def make_key(priv, plan, expiry, maxc, club, temp_password=""):
    """Пароль ВНУТРИ подписанного payload — клиент входит ровно по нему.
    Ключ БЕЗ дефисов: FIPRO-<raw>.<sig>. Возвращает (ключ, пароль)."""
    if not temp_password:
        temp_password = generate_temp_password()
    payload = {"plan": plan, "exp": expiry, "max_clients": maxc,
               "club": club, "club_id": club, "rnd": secrets.token_hex(4),
               "superadmin_login": "SuperAdmin",
               "temp_password": temp_password}
    raw = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(priv.sign(raw.encode())).decode().rstrip("=")
    return "FIPRO-" + raw + "." + sig, temp_password


def check_key(priv, key):
    try:
        token = key.replace("FIPRO-", "").strip()
        raw, sig = token.rsplit(".", 1)
        priv.public_key().verify(
            base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)), raw.encode())
    except InvalidSignature:
        return {"valid": False, "reason": "Подпись не совпадает — ключ недействителен"}
    except Exception as e:
        return {"valid": False, "reason": "Неверный формат: %s" % e}
    payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode())
    exp = datetime.strptime(payload["exp"], "%Y-%m-%d").date()
    payload["valid"] = exp >= date.today()
    if not payload["valid"]:
        payload["reason"] = "Истёк " + payload["exp"]
    return payload


class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FitIntel License Studio — ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА")
        self.priv = load_keys()
        w = QWidget()
        self.setCentralWidget(w)
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(
            "Приватный ключ: license_private.key (ТОЛЬКО у вас!). "
            "Ключи нового формата: FIPRO-... без дефисов внутри."))
        row = QHBoxLayout()
        self.cb_plan = QComboBox()
        self.cb_plan.addItems(PLANS)
        row.addWidget(self.cb_plan)
        self.sp_max = QSpinBox()
        self.sp_max.setRange(1, 100000)
        self.sp_max.setValue(300)
        row.addWidget(self.sp_max)
        self.dt_exp = QDateEdit(QDate.currentDate().addYears(1))
        self.dt_exp.setCalendarPopup(True)
        row.addWidget(self.dt_exp)
        self.ed_club = QLineEdit()
        self.ed_club.setPlaceholderText("Название клуба / клиента")
        row.addWidget(self.ed_club)
        lay.addLayout(row)
        btns = QHBoxLayout()
        b1 = QPushButton("Сгенерировать лицензию")
        b1.clicked.connect(self.gen)
        b2 = QPushButton("Проверить ключ")
        b2.clicked.connect(self.verify)
        b3 = QPushButton("Экспорт реестра CSV")
        b3.clicked.connect(self.export)
        for b in (b1, b2, b3):
            btns.addWidget(b)
        lay.addLayout(btns)
        self.ed_key = QLineEdit()
        self.ed_key.setPlaceholderText("Здесь появится ключ / вставь ключ для проверки")
        lay.addWidget(self.ed_key)
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["Тариф", "До", "Клиентов", "Клуб", "Ключ", "Temp пароль"])
        lay.addWidget(self.tbl)
        self.reload()
        self.resize(1000, 600)

    def registry(self):
        if os.path.exists(REG_FILE):
            try:
                return json.load(open(REG_FILE, encoding="utf-8"))
            except Exception:
                return []
        return []

    def save_registry(self, reg):
        json.dump(reg, open(REG_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    def reload(self):
        reg = self.registry()
        self.tbl.setRowCount(len(reg))
        for i, r in enumerate(reg):
            for j, k in enumerate(("plan", "exp", "max_clients", "club", "key", "temp_password")):
                self.tbl.setItem(i, j, QTableWidgetItem(str(r.get(k, ""))))

    def gen(self):
        plan = self.cb_plan.currentText()
        exp = self.dt_exp.date().toString("yyyy-MM-dd")
        club = self.ed_club.text().strip() or "-"
        key, temp_pass = make_key(self.priv, plan, exp, self.sp_max.value(), club)
        self.ed_key.setText(key)
        reg = self.registry()
        reg.append({"plan": plan, "exp": exp, "max_clients": self.sp_max.value(),
                    "club": club, "key": key,
                    "superadmin_login": "SuperAdmin", "temp_password": temp_pass})
        self.save_registry(reg)
        self.reload()
        QMessageBox.information(self, "Лицензия",
            "Ключ сгенерирован и записан в реестр.\n\nДАННЫЕ ДЛЯ КЛИЕНТА:\n"
            f"Лицензия: {key}\nЛогин: SuperAdmin\nПароль: {temp_pass}\n\n"
            "Клиент вводит эти данные при первом входе — пароль совпадает с ключом.")

    def verify(self):
        r = check_key(self.priv, self.ed_key.text())
        QMessageBox.information(self, "Проверка ключа",
                                json.dumps(r, ensure_ascii=False, indent=2))

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV", "licenses.csv", "CSV (*.csv)")
        if not path:
            return
        reg = self.registry()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            wtr = csv.DictWriter(f, fieldnames=["plan", "exp", "max_clients", "club",
                                                "key", "superadmin_login", "temp_password"],
                                 delimiter=";")
            wtr.writeheader()
            wtr.writerows(reg)
        QMessageBox.information(self, "Экспорт", "Сохранено: " + path)


print("License Studio starting...")
app = QApplication(sys.argv)
win = Studio()
win.show()
print("Window shown")
sys.exit(app.exec())