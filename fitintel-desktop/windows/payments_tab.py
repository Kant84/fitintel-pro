# -*- coding: utf-8 -*-
"""Платежи: провести, подтвердить, возврат, отмена, экспорт + проводки."""
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QFileDialog, QHeaderView, QTabWidget)
from . import theme
from .form_dialog import FormDialog

METHODS = ["CASH", "CARD", "SBP", "TRANSFER", "ONLINE", "SUBSCRIPTION",
           "QR", "BALANCE", "OTHER"]

def _t(name, *args):
    f = getattr(theme, name, None)
    if not callable(f):
        return ""
    for a in (args, ()):
        try:
            return f(*a)
        except TypeError:
            continue
        except Exception:
            return ""
    return ""

def _fio(c):
    f = c.get("fio") or c.get("full_name") or ""
    if not f:
        f = " ".join(x for x in [c.get("last_name"), c.get("first_name"),
                                 c.get("middle_name")] if x)
    return f or c.get("name") or c.get("email") or str(c.get("id"))

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))

class PaymentsTab(QWidget):
    COLS = ["ID", "Дата", "Сумма", "Метод", "Статус",
            "Направление", "Категория", "Комментарий"]
    ECOLS = ["ID", "Дата", "Дебет", "Кредит", "Сумма Дт", "Сумма Кт", "Описание"]

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self._clients = []
        self.setStyleSheet(_t("widget_style"))
        v = QVBoxLayout(self)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Клиент:"))
        self.cmb_client = QComboBox()
        self.cmb_client.setEditable(True)
        self.cmb_client.setMinimumWidth(340)
        bar.addWidget(self.cmb_client, 1)
        for text, slot in [("Обновить", self.reload_all),
                           ("＋ Провести платёж", self.add_payment),
                           ("✓ Подтвердить", self.complete_payment),
                           ("↩ Возврат", self.refund_payment),
                           ("✕ Отмена платежа", self.cancel_payment),
                           ("⇩ Экспорт CSV", self.export_csv)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        v.addLayout(bar)

        hint = QLabel("Отмена = возврат полной суммы (отдельного endpoint "
                      "отмены в API нет). Возврат — полный или частичный.")
        hint.setStyleSheet("color: %s;" % (_t("fg") and "#888" or "#888"))
        v.addWidget(hint)

        self.sub = QTabWidget()
        self.tbl = self._mk_table(self.COLS)
        self.tbl_e = self._mk_table(self.ECOLS)
        self.sub.addTab(self.tbl, "Платежи клиента")
        self.sub.addTab(self.tbl_e, "Проводки (бухгалтерия)")
        v.addWidget(self.sub, 1)

        self.cmb_client.currentIndexChanged.connect(lambda _i: self.load_payments())
        self.reload_all()

    def _mk_table(self, cols):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setStyleSheet(_t("table_style"))
        return t

    # ---------- infra ----------
    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda msg: self._show(msg, ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w)
                           if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    def reload_all(self):
        self._run(self.api.get_clients, self._fill_clients)
        self._run(self.api.get_accounting_entries, self._fill_entries)

    # ---------- clients / payments ----------
    def _fill_clients(self, data):
        self._clients = data if isinstance(data, list) else []
        cur = self.cmb_client.currentData()
        self.cmb_client.blockSignals(True)
        self.cmb_client.clear()
        for c in self._clients:
            label = "%s — %s" % (_fio(c), c.get("phone") or c.get("id"))
            self.cmb_client.addItem(label, c.get("id"))
        if cur is not None:
            i = self.cmb_client.findData(cur)
            if i >= 0:
                self.cmb_client.setCurrentIndex(i)
        self.cmb_client.blockSignals(False)
        self.load_payments()

    def _cid(self):
        cid = self.cmb_client.currentData()
        if cid is None:
            self._show("Сначала выбери клиента из списка.", ok=False)
        return cid

    def load_payments(self):
        cid = self.cmb_client.currentData()
        if cid is None:
            return
        self._run(lambda: self.api.get_client_payments(cid), self._fill_pays)

    def _fill_pays(self, data):
        rows = data if isinstance(data, list) else []
        self.tbl.setRowCount(0)
        for p in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            pid = p.get("id") or p.get("payment_id")
            vals = [str(pid)[:8],
                    str(p.get("created_at") or p.get("payment_date") or "")[:19],
                    str(p.get("amount") or ""),
                    p.get("payment_method") or p.get("method") or "",
                    p.get("status") or "",
                    p.get("payment_direction") or "",
                    p.get("payment_category") or "",
                    p.get("notes") or ""]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if j == 0:
                    it.setData(Qt.ItemDataRole.UserRole, pid)
                self.tbl.setItem(r, j, it)
        self._show("Платежей: %d" % len(rows))

    def _selected_pid(self):
        r = self.tbl.currentRow()
        if r < 0:
            self._show("Выбери платёж в таблице.", ok=False)
            return None
        it = self.tbl.item(r, 0)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    # ---------- actions ----------
    def add_payment(self):
        cid = self._cid()
        if cid is None:
            return
        dlg = FormDialog([
            ("amount", "Сумма", "text", None),
            ("method", "Способ оплаты", "combo", METHODS),
            ("direction", "Направление", "combo", ["", "INCOMING", "OUTGOING"]),
            ("category", "Категория", "combo",
             ["", "SUBSCRIPTION", "SERVICE", "PRODUCT", "OTHER"]),
            ("notes", "Комментарий", "text", None)], self)
        if not dlg.exec():
            return
        v = dlg.values()
        try:
            amount = float(str(v.get("amount", "")).replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            self._show("Сумма должна быть положительным числом.", ok=False)
            return
        self._run(lambda: self.api.create_payment(
            amount, v.get("method") or "CASH", client_id=cid,
            notes=v.get("notes") or None,
            direction=v.get("direction") or None,
            category=v.get("category") or None),
            lambda _r: (self._show("Платёж проведён."), self.load_payments()))

    def complete_payment(self):
        pid = self._selected_pid()
        if pid is None:
            return
        self._run(lambda: self.api.complete_payment(pid),
                  lambda _r: (self._show("Платёж подтверждён."),
                              self.load_payments()))

    def refund_payment(self):
        pid = self._selected_pid()
        if pid is None:
            return
        dlg = FormDialog([
            ("amount", "Сумма возврата (пусто = полная)", "text", None),
            ("reason", "Причина возврата", "text", None)], self)
        if not dlg.exec():
            return
        v = dlg.values()
        reason = (v.get("reason") or "").strip()
        if not reason:
            self._show("Причина возврата обязательна.", ok=False)
            return
        amount = (v.get("amount") or "").strip() or None
        self._run(lambda: self.api.refund_payment(pid, reason, amount),
                  lambda _r: (self._show("Возврат оформлен."),
                              self.load_payments()))

    def cancel_payment(self):
        pid = self._selected_pid()
        if pid is None:
            return
        if QMessageBox.warning(self, "Отмена платежа",
                "Отменить платёж полностью?\n"
                "Будет оформлен возврат полной суммы.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._run(lambda: self.api.refund_payment(pid, "Отмена платежа"),
                  lambda _r: (self._show("Платёж отменён (возврат полной суммы)."),
                              self.load_payments()))

    def export_csv(self):
        path, _f = QFileDialog.getSaveFileName(self, "Экспорт платежей",
                                               "payments.csv", "CSV (*.csv)")
        if not path:
            return
        cid = self.cmb_client.currentData()

        def _save(res):
            if isinstance(res, str):
                text = res
            elif isinstance(res, (bytes, bytearray)):
                text = bytes(res).decode("utf-8-sig", "replace")
            else:
                text = json.dumps(res, ensure_ascii=False, indent=2, default=str)
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(text)
            self._show("Экспорт сохранён: %s" % path)

        self._run(lambda: self.api.export_payments(client_id=cid, fmt="csv"), _save)

    # ---------- accounting entries ----------
    def _fill_entries(self, data):
        rows = data if isinstance(data, list) else []
        self.tbl_e.setRowCount(0)
        for e in rows:
            r = self.tbl_e.rowCount()
            self.tbl_e.insertRow(r)
            vals = [str(e.get("id") or "")[:8],
                    str(e.get("entry_date") or e.get("created_at") or "")[:19],
                    e.get("debit_account") or "",
                    e.get("credit_account") or "",
                    str(e.get("debit") or ""),
                    str(e.get("credit") or ""),
                    e.get("description") or ""]
            for j, val in enumerate(vals):
                self.tbl_e.setItem(r, j, QTableWidgetItem(str(val)))


# === E63_PRINT ===
try:
    from windows.print_helper import add_print_button as _e63_apb
    _e63_orig = PaymentsTab.__init__
    def _e63_init(self, *a, **kw):
        _e63_orig(self, *a, **kw)
        try:
            _e63_apb(self, "Платежи")
        except Exception as e:
            print("print btn:", e)
    PaymentsTab.__init__ = _e63_init
    print("E63 print OK: payments_tab.py")
except Exception as e:
    print("E63 FAIL:", e)
