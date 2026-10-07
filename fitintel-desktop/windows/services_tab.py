"""FitIntel Pro — Services Tab (услуги клуба: список, создание, тренер, удаление)"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QCheckBox, QTabWidget, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QColor

from api import ApiClient
from windows import theme

CATEGORIES = ["SAUNA", "SOLARIUM", "POOL", "MASSAGE", "AEROBICS",
              "DANCE", "PERSONAL_TRAINER"]
CAT_RU = {"SAUNA": "Сауна", "SOLARIUM": "Солярий", "POOL": "Бассейн",
          "MASSAGE": "Массаж", "AEROBICS": "Аэробика", "DANCE": "Танцы",
          "PERSONAL_TRAINER": "Перс. тренировка"}


def _trainer_name(p: dict, umap: dict | None = None) -> str:
    uid = str(p.get("user_id") or p.get("id") or "")
    if umap and uid in umap:
        return umap[uid]
    for k in ("full_name", "name", "username", "fio"):
        if p.get(k):
            return str(p[k])
    spec = p.get("specialization") or ""
    return f"{spec} ({uid[:8]})" if spec else (uid[:8] or "—")


class ServicesWorker(QThread):
    finished = pyqtSignal(list, list, list)
    error = pyqtSignal(str)

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

    def run(self):
        try:
            r1 = self.api.session.get(self.api._url("services"))
            r1.raise_for_status()
            services = r1.json()
            try:
                r2 = self.api.session.get(self.api._url("trainers/profiles"))
                trainers = r2.json() if r2.status_code == 200 else []
            except Exception:
                trainers = []
            try:
                r3 = self.api.session.get(self.api._url("users"))
                users = r3.json() if r3.status_code == 200 else []
                if isinstance(users, dict):
                    users = users.get("items", []) 
            except Exception:
                users = []
            self.finished.emit(services if isinstance(services, list) else [],
                               trainers if isinstance(trainers, list) else [],
                               users if isinstance(users, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class ServiceDialog(QDialog):
    """Создание/редактирование услуги (тренер — опционально)"""

    def __init__(self, api: ApiClient, trainers: list, users: list,
                 service: dict | None = None, parent=None):
        super().__init__(parent)
        self.api = api
        self.service = service or {}
        self.ok = False
        self.setWindowTitle("Услуга" if service else "Новая услуга")
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.name = QLineEdit(self.service.get("name", ""))
        form.addRow("Название:", self.name)

        self.category = QComboBox()
        for c in CATEGORIES:
            self.category.addItem(CAT_RU.get(c, c), c)
        cur = self.service.get("category")
        if cur in CATEGORIES:
            self.category.setCurrentIndex(CATEGORIES.index(cur))
        form.addRow("Категория:", self.category)

        self.price = QDoubleSpinBox()
        self.price.setRange(1, 1000000)
        self.price.setDecimals(2)
        self.price.setValue(float(self.service.get("price") or 500))
        form.addRow("Цена, ₽:", self.price)

        self.duration = QSpinBox()
        self.duration.setRange(1, 600)
        self.duration.setValue(int(self.service.get("duration_minutes") or 60))
        form.addRow("Длительность, мин:", self.duration)

        self.capacity = QSpinBox()
        self.capacity.setRange(1, 200)
        self.capacity.setValue(int(self.service.get("max_capacity") or 1))
        form.addRow("Вместимость:", self.capacity)

        # тренер: имена подтягиваем из списка пользователей
        umap = {}
        for u in users:
            nm = u.get("full_name") or u.get("username") or u.get("name")
            if nm and u.get("id"):
                umap[str(u["id"])] = str(nm)

        self.trainer = QComboBox()
        self.trainer.addItem("без тренера —", None)
        for p in trainers:
            self.trainer.addItem(_trainer_name(p, umap),
                                 p.get("user_id") or p.get("id"))
        tid = self.service.get("trainer_id")
        if tid:
            for i in range(self.trainer.count()):
                if str(self.trainer.itemData(i)) == str(tid):
                    self.trainer.setCurrentIndex(i)
                    break
        form.addRow("Тренер:", self.trainer)

        self.active = QCheckBox("Активна")
        self.active.setChecked(bool(self.service.get("is_active", True)))
        form.addRow(self.active)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _submit(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Услуга", "Введите название")
            return
        if float(self.price.value()) <= 0:
            QMessageBox.warning(self, "Услуга", "Цена должна быть больше 0")
            return
        payload = {
            "name": name,
            "category": self.category.currentData(),
            "price": float(self.price.value()),
            "duration_minutes": int(self.duration.value()),
            "max_capacity": int(self.capacity.value()),
            "is_active": bool(self.active.isChecked()),
            "trainer_id": self.trainer.currentData(),
        }
        try:
            if self.service.get("id"):
                resp = self.api.session.put(
                    self.api._url(f"services/{self.service['id']}"),
                    json={k: v for k, v in payload.items()
                          if k in ("name", "price", "is_active", "max_capacity",
                                   "duration_minutes", "category", "trainer_id")})
            else:
                resp = self.api.session.post(self.api._url("services"), json=payload)
            if resp.status_code in (200, 201):
                self.ok = True
                self.accept()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Не сохранено", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

class TrainerDialog(QDialog):
    """Создание профиля тренера для существующего пользователя"""

    def __init__(self, api: ApiClient, users: list, existing_user_ids: set, parent=None):
        super().__init__(parent)
        self.api = api
        self.ok = False
        self.setWindowTitle("Новый тренер")
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.user = QComboBox()
        self._uids = []
        shown = 0
        for u in users:
            uid = u.get("id")
            if not uid or str(uid) in existing_user_ids:
                continue  # пропускаем тех, у кого уже есть профиль тренера
            nm = u.get("full_name") or u.get("username") or u.get("email") or str(uid)[:8]
            self._uids.append(uid)
            self.user.addItem(str(nm))
            shown += 1
        form.addRow("Пользователь:", self.user)
        if shown == 0:
            QMessageBox.information(self, "Новый тренер",
                                    "Все пользователи уже имеют профили тренеров.\n"
                                    "Сначала создайте пользователя во вкладке «Пользователи».")

        self.spec = QLineEdit()
        self.spec.setPlaceholderText("например: Бодибилдинг")
        form.addRow("Специализация:", self.spec)

        self.rate = QDoubleSpinBox()
        self.rate.setRange(0, 1000000)
        self.rate.setValue(1000)
        form.addRow("Ставка, ₽/час:", self.rate)

        self.comm = QDoubleSpinBox()
        self.comm.setRange(0, 100)
        self.comm.setValue(10)
        form.addRow("Комиссия, %:", self.comm)

        self.max_clients = QSpinBox()
        self.max_clients.setRange(1, 50)
        self.max_clients.setValue(8)
        form.addRow("Макс. клиентов/день:", self.max_clients)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Создать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _submit(self):
        if not self._uids:
            self.reject()
            return
        payload = {
            "user_id": str(self._uids[self.user.currentIndex()]),
            "specialization": self.spec.text().strip() or None,
            "rate_per_hour": float(self.rate.value()),
            "commission_percent": float(self.comm.value()),
            "max_clients_per_day": int(self.max_clients.value()),
        }
        try:
            resp = self.api.session.post(self.api._url("trainers/profiles"), json=payload)
            if resp.status_code == 201:
                self.ok = True
                self.accept()
            else:
                detail = "ошибка сервера"
                try:
                    detail = resp.json().get("detail", detail)
                except Exception:
                    pass
                QMessageBox.warning(self, "Не создано", f"{resp.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
class ShopTab(QWidget):
    """Волна 5: Магазин (склад) — каталог + продажа на кассу (нал/карта/СБП)."""
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._products = []
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        self.lbl_info = QLabel("Каталог склада (продажа — на кассе, оплата любым способом).")
        top.addWidget(self.lbl_info)
        top.addStretch()
        btn_sell = QPushButton("Продать")
        btn_sell.setStyleSheet("QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_sell.clicked.connect(self._sell)
        btn_ref = QPushButton("Обновить")
        btn_ref.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_sell)
        top.addWidget(btn_ref)
        v.addLayout(top)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Товар", "Цена ₽", "Остаток", "Ед."])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setStyleSheet(theme.table_style())
        v.addWidget(self.tbl, 1)
        self.refresh()

    def refresh(self):
        try:
            r = self.api.session.get(self.api._url("warehouse/products"), params={"club_id": 1})
            if r.status_code != 200:
                self.tbl.setRowCount(1)
                self.tbl.setItem(0, 0, QTableWidgetItem(f"Склад недоступен: {r.status_code}"))
                return
            rows = r.json()
            self._products = rows if isinstance(rows, list) else rows.get("items", [])
            self.tbl.setRowCount(len(self._products))
            for i, p in enumerate(self._products):
                self.tbl.setItem(i, 0, QTableWidgetItem(str(p.get("name") or "—")))
                self.tbl.setItem(i, 1, QTableWidgetItem(str(p.get("sale_price") or 0)))
                self.tbl.setItem(i, 2, QTableWidgetItem(str(p.get("quantity") or 0)))
                self.tbl.setItem(i, 3, QTableWidgetItem(str(p.get("unit") or "шт")))
        except Exception as e:
            self.tbl.setRowCount(1)
            self.tbl.setItem(0, 0, QTableWidgetItem(f"Ошибка: {e}"))

    def _sell(self):
        idx = self.tbl.currentRow()
        if idx < 0 or idx >= len(self._products):
            QMessageBox.information(self, "Продажа", "Выберите товар в таблице")
            return
        p = self._products[idx]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Продажа: {p.get('name')}")
        f = QFormLayout(dlg)
        qty = QSpinBox(); qty.setRange(1, int(float(p.get("quantity") or 0)) or 1); qty.setValue(1)
        f.addRow("Количество:", qty)
        pay = QComboBox(); pay.addItem("Наличные", "cash"); pay.addItem("Карта", "card"); pay.addItem("СБП", "sbp")
        f.addRow("Оплата:", pay)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Провести")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            r = self.api.session.post(self.api._url("warehouse/bar/sales"), json={
                "club_id": 1,
                "payment_method": pay.currentData(),
                "items": [{"item_type": "product",
                           "product_id": str(p.get("id")),
                           "quantity": qty.value()}]})
            if r.status_code == 201:
                d = r.json()
                QMessageBox.information(self, "Продажа", f"Продано на {d.get('total', 0):.2f} ₽")
                self.refresh()
            else:
                detail = "ошибка сервера"
                try: detail = r.json().get("detail", detail)
                except Exception: pass
                QMessageBox.warning(self, "Не проведено", f"{r.status_code}: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


class ServicesTab(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._services = []
        self._trainers = []
        self._users = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tabs = QTabWidget()
        host = QWidget()
        inner = QVBoxLayout(host)
        inner.setContentsMargins(16, 16, 16, 16)
        inner.setSpacing(12)
        layout.addWidget(tabs)

        row = QHBoxLayout()
        for text, handler, style in (
            ("Добавить услугу", self._add,
             "QPushButton { background: #059669; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }"),
            ("Назначить тренера", self._edit,
             "QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }"),
            ("Удалить", self._delete,
             "QPushButton { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; border-radius: 6px; padding: 8px 16px; font-weight: 600; }"),
            ("Новый тренер", self._new_trainer,
             "QPushButton { background: #eef2ff; border: 1px solid #a5b4fc; color: #3730a3; border-radius: 6px; padding: 8px 16px; font-weight: 600; }"),
        ):
            b = QPushButton(text)
            b.setStyleSheet(style)
            b.clicked.connect(handler)
            row.addWidget(b)
        row.addStretch()
        rb = QPushButton("Обновить")
        rb.setStyleSheet("QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: 600; }")
        rb.clicked.connect(self.refresh)
        row.addWidget(rb)
        inner.addLayout(row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Категория", "Цена ₽", "Мин", "Мест", "Тренер", "Активна"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme.table_style())
        inner.addWidget(self.table)
        tabs.addTab(host, "Услуги")
        self._shop = ShopTab(self.api)
        tabs.addTab(self._shop, "Магазин")

    def refresh(self):
        self.worker = ServicesWorker(self.api)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_loaded(self, services: list, trainers: list, users: list):
        self._services = services
        self._trainers = trainers
        self._users = users

        umap = {}
        for u in users:
            nm = u.get("full_name") or u.get("username") or u.get("name")
            if nm and u.get("id"):
                umap[str(u["id"])] = str(nm)

        tmap = {}
        for p in trainers:
            tmap[str(p.get("user_id") or p.get("id"))] = _trainer_name(p, umap)

        self.table.setRowCount(max(len(services), 1))
        if not services:
            self.table.setItem(0, 0, QTableWidgetItem("Услуг пока нет — нажмите «Добавить услугу»"))
            self.table.setSpan(0, 0, 1, 7)
            return
        for i, s in enumerate(services):
            self.table.setItem(i, 0, QTableWidgetItem(str(s.get("name") or "—")))
            cat = str(s.get("category") or "—")
            self.table.setItem(i, 1, QTableWidgetItem(CAT_RU.get(cat, cat)))
            self.table.setItem(i, 2, QTableWidgetItem(str(s.get("price") or 0)))
            self.table.setItem(i, 3, QTableWidgetItem(str(s.get("duration_minutes") or "—")))
            self.table.setItem(i, 4, QTableWidgetItem(str(s.get("max_capacity") or 1)))
            tid = s.get("trainer_id")
            self.table.setItem(i, 5, QTableWidgetItem(tmap.get(str(tid), "—") if tid else "—"))
            act = QTableWidgetItem("да" if s.get("is_active") else "нет")
            if not s.get("is_active"):
                act.setForeground(QColor("#ef4444"))
            self.table.setItem(i, 6, act)

    def _on_error(self, msg: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(f"Ошибка загрузки: {msg}"))
        self.table.setSpan(0, 0, 1, 7)

    def _selected(self) -> dict | None:
        idx = self.table.currentRow()
        return self._services[idx] if 0 <= idx < len(self._services) else None

    def _add(self):
        dlg = ServiceDialog(self.api, self._trainers, self._users, parent=self)
        if dlg.exec() and dlg.ok:
            QMessageBox.information(self, "Услуги", "Услуга создана")
            self.refresh()

    def _edit(self):
        s = self._selected()
        if not s:
            QMessageBox.information(self, "Услуги", "Выберите услугу в таблице")
            return
        dlg = ServiceDialog(self.api, self._trainers, self._users, service=s, parent=self)
        if dlg.exec() and dlg.ok:
            self.refresh()

    def _delete(self):
        s = self._selected()
        if not s:
            QMessageBox.information(self, "Услуги", "Выберите услугу в таблице")
            return
        if QMessageBox.question(
                self, "Удаление услуги",
                f"Удалить услугу «{s.get('name')}»?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            resp = self.api.session.delete(self.api._url(f"services/{s['id']}"))
            if resp.status_code == 204:
                self.refresh()
            else:
                QMessageBox.warning(self, "Не удалено", f"Код: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            
            
    def _new_trainer(self):
        existing = {str(p.get("user_id") or p.get("id")) for p in self._trainers}
        dlg = TrainerDialog(self.api, self._users, existing, parent=self)
        if dlg.exec() and getattr(dlg, "ok", False):
            QMessageBox.information(self, "Тренеры", "Профиль тренера создан")
            self.refresh()      