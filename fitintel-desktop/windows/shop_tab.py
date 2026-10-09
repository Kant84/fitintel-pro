"""Магазин (склад): серверный режим (warehouse API) или ЛОКАЛЬНАЯ ЭМУЛЯЦИЯ-КИОСК.

Если серверный склад недоступен (500/сеть) — вкладка работает на локальном JSON:
товары вносятся через «Добавить товар», фото грузится ФАЙЛОМ (копия в shop_photos/),
«Продать» списывает количество и пишет журнал продаж. Данные — рядом с клиентом:
    shop_products.json, shop_sales.json, shop_photos/
"""
import json
import os
import shutil
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QDialogButtonBox, QFileDialog,
)

from api import ApiClient
from windows import theme

DATA_DIR = Path(__file__).parents[1]
SHOP_SETTINGS = DATA_DIR / "shop_settings.json"
PRODUCTS_JSON = DATA_DIR / "shop_products.json"
SALES_JSON = DATA_DIR / "shop_sales.json"
PHOTOS_DIR = DATA_DIR / "shop_photos"


class _PhotoLoader(QThread):
    done = pyqtSignal(object)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        px = QPixmap()
        try:
            with urllib.request.urlopen(self.url, timeout=8) as r:
                px.loadFromData(r.read())
        except Exception:
            pass
        self.done.emit(px)


class ShopTab(QWidget):
    COLUMNS = ["Наименование", "Артикул", "Фото", "Количество", "Цена ₽", "Ед."]

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self._products = []
        self._server_mode = None          # None неизвестно, True сервер, False эмуляция
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        self.lbl_info = QLabel("")
        top.addWidget(self.lbl_info, 1)
        for text, slot, color, fg in (
            ("Продать", self._sell, "#059669", "white"),
            ("＋ Добавить товар", self._add_product, "#10b981", "white"),
            ("Изменить", self._edit_product, "#f1f5f9", "#475569"),
            ("Удалить", self._delete_product, "#fee2e2", "#b91c1c"),
            ("Загрузить фото", self._upload_photo, "#eef2ff", "#3730a3"),
            ("Настройки Магазина", self._settings_dialog, "#fdf4ff", "#a21caf"),
            ("Обновить", self.refresh, "#f1f5f9", "#475569"),
        ):
            b = QPushButton(text)
            b.setStyleSheet(f"QPushButton {{ background: {color}; color: {fg}; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; font-weight: 600; }}")
            b.clicked.connect(slot)
            top.addWidget(b)
        v.addLayout(top)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(len(self.COLUMNS))
        self.tbl.setHorizontalHeaderLabels(self.COLUMNS)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setStyleSheet(theme.table_style())
        v.addWidget(self.tbl, 1)
        self.refresh()

    # ---------- настройки ----------

    def _shop_cfg(self) -> dict:
        try:
            if SHOP_SETTINGS.exists():
                return json.loads(SHOP_SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"mode": "auto", "club_id": 1}

    def _settings_dialog(self):
        from PyQt6.QtWidgets import QComboBox, QDialogButtonBox
        cfg = self._shop_cfg()
        dlg = QDialog(self)
        dlg.setWindowTitle("Настройки Магазина")
        f = QFormLayout(dlg)
        cb = QComboBox()
        cb.addItem("Авто (сервер, при сбое — киоск)", "auto")
        cb.addItem("Только серверный склад", "server")
        cb.addItem("Только локальный киоск", "kiosk")
        cb.setCurrentIndex({"auto": 0, "server": 1, "kiosk": 2}.get(cfg.get("mode", "auto"), 0))
        sp = QSpinBox(); sp.setRange(1, 999999); sp.setValue(int(cfg.get("club_id", 1)))
        f.addRow("Режим склада:", cb)
        f.addRow("ID клуба (склад):", sp)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            SHOP_SETTINGS.write_text(json.dumps({"mode": cb.currentData(), "club_id": sp.value()},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
            self.refresh()

    # ---------- данные ----------

    def refresh(self):
        cfg = self._shop_cfg()
        if cfg.get("mode") == "kiosk":
            self._switch_kiosk("Режим: локальный киоск (shop_settings.json)")
            return
        if cfg.get("mode") == "server":
            self._load_server(cfg, force=True)
            return
        self._load_server(cfg, force=False)

    def _load_server(self, cfg, force: bool):
        try:
            r = self.api.session.get(self.api._url("/warehouse/products"),
                                     params={"club_id": int(cfg.get("club_id", 1))}, timeout=8)
            if r.status_code == 200:
                rows = r.json()
                self._products = rows if isinstance(rows, list) else rows.get("items", [])
                self._server_mode = True
                self.lbl_info.setText(f"Серверный склад (warehouse, клуб {cfg.get('club_id', 1)})")
                self._render()
                return
        except Exception:
            pass
        if force:
            self._server_mode = True
            self._products = []
            self.lbl_info.setText(f"Серверный склад недоступен (клуб {cfg.get('club_id', 1)}): {r.status_code if 'r' in dir() else 'сеть'} — проверьте warehouse на сервере")
            self._render()
            return
        self._switch_kiosk("Локальная эмуляция склада (киоск): данные в shop_products.json")

    def _switch_kiosk(self, label: str):
        self._server_mode = False
        self.lbl_info.setText(label)
        self._products = self._load_local()
        self._render()

    def _load_local(self):
        try:
            if PRODUCTS_JSON.exists():
                return json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
        # демо-ассортимент киоска при первом запуске
        demo = [
            {"id": uuid.uuid4().hex[:12], "article": "PR-001", "name": "Протеиновый коктейль 300мл",
             "quantity": 25, "sale_price": 250.0, "unit": "шт", "photo_url": ""},
            {"id": uuid.uuid4().hex[:12], "article": "VD-003", "name": "Вода негазированная 0.5л",
             "quantity": 120, "sale_price": 60.0, "unit": "шт", "photo_url": ""},
            {"id": uuid.uuid4().hex[:12], "article": "BR-002", "name": "Батончик энергетический",
             "quantity": 60, "sale_price": 120.0, "unit": "шт", "photo_url": ""},
        ]
        self._save_local(demo)
        return demo

    def _save_local(self, rows):
        PRODUCTS_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

    # ---------- отрисовка ----------

    def _render(self):
        self.tbl.setRowCount(len(self._products))
        for i, p in enumerate(self._products):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(p.get("name") or "—")))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(p.get("article") or "—")))
            photo = QLabel("—")
            photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            url = str(p.get("photo_url") or "")
            if url:
                if url.startswith("http"):
                    loader = _PhotoLoader(url)
                    loader.done.connect(lambda px, lbl=photo: self._set_photo(lbl, px))
                    loader.start()
                elif os.path.exists(url):
                    self._set_photo(photo, QPixmap(url))
            self.tbl.setCellWidget(i, 2, photo)
            self.tbl.setRowHeight(i, 56)
            self.tbl.setItem(i, 3, QTableWidgetItem(str(p.get("quantity") or 0)))
            self.tbl.setItem(i, 4, QTableWidgetItem(str(p.get("sale_price") or 0)))
            self.tbl.setItem(i, 5, QTableWidgetItem(str(p.get("unit") or "шт")))

    def _set_photo(self, lbl, px):
        if px and not px.isNull():
            lbl.setPixmap(px.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))

    # ---------- диалог товара ----------

    def _product_dialog(self, p=None):
        p = p or {}
        dlg = QDialog(self)
        dlg.setWindowTitle("Товар" if p else "Новый товар")
        f = QFormLayout(dlg)
        ed_name = QLineEdit(str(p.get("name") or ""))
        ed_art = QLineEdit(str(p.get("article") or ""))
        sp_qty = QSpinBox(); sp_qty.setRange(0, 1000000); sp_qty.setValue(int(float(p.get("quantity") or 0)))
        sp_price = QDoubleSpinBox(); sp_price.setRange(0, 10000000); sp_price.setValue(float(p.get("sale_price") or 0))
        ed_unit = QLineEdit(str(p.get("unit") or "шт"))
        ed_photo = QLineEdit(str(p.get("photo_url") or ""))
        ed_photo.setPlaceholderText("не обязательно — можно загрузить файлом кнопкой")
        f.addRow("Наименование:", ed_name)
        f.addRow("Артикул:", ed_art)
        f.addRow("Количество:", sp_qty)
        f.addRow("Цена ₽:", sp_price)
        f.addRow("Ед.:", ed_unit)
        f.addRow("Фото (URL):", ed_photo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        if not ed_name.text().strip():
            QMessageBox.warning(self, "Товар", "Укажите наименование")
            return None
        return {"name": ed_name.text().strip(), "article": ed_art.text().strip(),
                "quantity": sp_qty.value(), "sale_price": float(sp_price.value()),
                "unit": ed_unit.text().strip() or "шт",
                "photo_url": ed_photo.text().strip()}

    # ---------- CRUD ----------

    def _selected(self):
        idx = self.tbl.currentRow()
        if 0 <= idx < len(self._products):
            return idx, self._products[idx]
        QMessageBox.information(self, "Товар", "Выберите товар в таблице")
        return None, None

    def _add_product(self):
        data = self._product_dialog()
        if not data:
            return
        if self._server_mode:
            data["club_id"] = 1
            r = self.api.session.post(self.api._url("/warehouse/products-create"), json=data)
            (self.refresh() if r.status_code == 201 else
             QMessageBox.warning(self, "Товар", f"{r.status_code}: {r.text[:150]}"))
        else:
            data["id"] = uuid.uuid4().hex[:12]
            self._products.append(data)
            self._save_local(self._products)
            self._render()

    def _edit_product(self):
        idx, p = self._selected()
        if p is None:
            return
        data = self._product_dialog(p)
        if not data:
            return
        if self._server_mode:
            r = self.api.session.put(self.api._url(f"/warehouse/products/{p['id']}"), json=data)
            (self.refresh() if r.status_code == 200 else
             QMessageBox.warning(self, "Товар", f"{r.status_code}: {r.text[:150]}"))
        else:
            data["id"] = p.get("id")
            data["photo_url"] = data["photo_url"] or p.get("photo_url", "")
            self._products[idx] = data
            self._save_local(self._products)
            self._render()

    def _delete_product(self):
        idx, p = self._selected()
        if p is None:
            return
        if QMessageBox.question(self, "Удаление товара", f"Удалить «{p.get('name')}»?"
                                ) != QMessageBox.StandardButton.Yes:
            return
        if self._server_mode:
            r = self.api.session.delete(self.api._url(f"/warehouse/products/{p['id']}"))
            (self.refresh() if r.status_code == 204 else
             QMessageBox.warning(self, "Товар", f"{r.status_code}: {r.text[:150]}"))
        else:
            del self._products[idx]
            self._save_local(self._products)
            self._render()

    def _upload_photo(self):
        idx, p = self._selected()
        if p is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Фото товара", "",
                                              "Изображения (*.jpg *.jpeg *.png *.webp)")
        if not path:
            return
        if self._server_mode:
            try:
                with open(path, "rb") as fh:
                    r = self.api.session.post(
                        self.api._url(f"/warehouse/products/{p['id']}/photo"),
                        files={"file": (os.path.basename(path), fh, "image/jpeg")})
                if r.status_code == 200:
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Фото", f"{r.status_code}: {r.text[:150]}")
            except Exception as e:
                QMessageBox.critical(self, "Фото", str(e))
        else:
            PHOTOS_DIR.mkdir(exist_ok=True)
            ext = path.rsplit(".", 1)[-1].lower()[:4]
            dst = PHOTOS_DIR / f"{p.get('id')}.{ext}"
            try:
                shutil.copyfile(path, dst)
            except Exception as e:
                QMessageBox.critical(self, "Фото", str(e))
                return
            self._products[idx]["photo_url"] = str(dst)
            self._save_local(self._products)
            self._render()

    # ---------- продажа ----------

    def _kiosk_client_id(self):
        """Служебный клиент «Киоск (розница)» — для платежей магазина без карточки покупателя."""
        try:
            for c in self.api.get_clients():
                if c.get("phone") == "+70000000000":
                    return c.get("id")
            return self.api.create_client({
                "first_name": "Киоск", "last_name": "(розница)",
                "phone": "+70000000000",
            }) and self._kiosk_client_id()
        except Exception:
            return None

    def _create_payment(self, product, qty, method, total):
        """Продажа товара -> платёж в «Платежи» (статус «Ожидает», категория Товар).
        Кассир подтверждает платёж чеком как обычно. Неудача платежа НЕ отменяет продажу.
        Схема кассы клиенто-зависимая: пробуем без клиента, потом со служебным «Киоск»."""
        method_up = str(method or "cash").upper()
        notes = f"Магазин: {product.get('name')} ×{qty}"
        attempts = [
            lambda: self.api.create_payment(total, method_up, notes=notes,
                                            direction="INCOMING", category="PRODUCT"),
        ]
        kiosk = self._kiosk_client_id()
        if kiosk:
            attempts.insert(0, lambda: self.api.create_payment(
                total, method_up, client_id=kiosk, notes=notes,
                direction="INCOMING", category="PRODUCT"))
        last_err = None
        for att in attempts:
            try:
                att()
                QMessageBox.information(
                    self, "Продажа",
                    f"Продано на {total:.2f} ₽.\n"
                    f"Платёж создан в «Платежи» со статусом «Ожидает» — кассир подтвердит чеком.")
                return True
            except Exception as e:
                last_err = e
        QMessageBox.warning(
            self, "Платёж",
            f"Продажа проведена, но платёж НЕ создан ({last_err}).\n"
            f"Создайте платёж вручную в «Платежи» (сумма {total:.2f} ₽).")
        return False

    def _sell(self):
        idx, p = self._selected()
        if p is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Продажа: {p.get('name')}")
        f = QFormLayout(dlg)
        qty = QSpinBox(); qty.setRange(1, int(float(p.get("quantity") or 0)) or 1); qty.setValue(1)
        f.addRow("Количество:", qty)
        from PyQt6.QtWidgets import QComboBox
        pay = QComboBox(); pay.addItem("Наличные", "cash"); pay.addItem("Карта", "card"); pay.addItem("СБП", "sbp")
        f.addRow("Оплата:", pay)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Провести")
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if self._server_mode:
            try:
                r = self.api.session.post(self.api._url("/warehouse/bar/sales"), json={
                    "club_id": 1, "payment_method": pay.currentData(),
                    "items": [{"item_type": "product", "product_id": str(p.get("id")),
                               "quantity": qty.value()}]})
                d = r.json() if r.status_code == 201 else {}
                if r.status_code == 201:
                    total = float(d.get("total", 0))
                    self._create_payment(p, qty.value(), pay.currentData(), total)
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Продажа", f"{r.status_code}: {r.text[:150]}")
            except Exception as e:
                QMessageBox.critical(self, "Продажа", str(e))
        else:
            left = int(float(p.get("quantity") or 0)) - qty.value()
            if left < 0:
                QMessageBox.warning(self, "Продажа", "Недостаточно остатка")
                return
            self._products[idx]["quantity"] = left
            self._save_local(self._products)
            sale = {"at": datetime.now().isoformat(timespec="seconds"),
                    "product": p.get("name"), "article": p.get("article"),
                    "quantity": qty.value(),
                    "price": float(p.get("sale_price") or 0) * qty.value(),
                    "payment": pay.currentText()}
            sales = []
            if SALES_JSON.exists():
                try:
                    sales = json.loads(SALES_JSON.read_text(encoding="utf-8"))
                except Exception:
                    sales = []
            sales.append(sale)
            SALES_JSON.write_text(json.dumps(sales, ensure_ascii=False, indent=2), encoding="utf-8")
            self._create_payment(p, qty.value(), pay.currentData(), sale["price"])
            self._render()