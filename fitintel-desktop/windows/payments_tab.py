# -*- coding: utf-8 -*-
"""Платежи: провести, подтвердить, возврат, отмена, экспорт + проводки + кассовая смена (E31/E33)."""
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QFileDialog, QHeaderView, QTabWidget)
from . import theme
from .form_dialog import FormDialog
from datetime import datetime, timezone

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
    
# === Кириллица (E33) ===
RU_M = {"CASH": "Наличные", "CARD": "Карта", "SBP": "СБП (по QR)",
        "TRANSFER": "Перевод", "ONLINE": "Онлайн-оплата",
        "SUBSCRIPTION": "Абонемент (зачёт)", "QR": "QR-код",
        "BALANCE": "Внутренний баланс", "OTHER": "Другое"}
RU_D = {"INCOMING": "Приход", "OUTGOING": "Расход",
        "INCOME": "Приход", "EXPENSE": "Расход", "OUTCOME": "Расход"}
RU_C = {"SUBSCRIPTION": "Абонемент", "SERVICE": "Услуга",
        "PRODUCT": "Товар", "OTHER": "Прочее"}
RU_S = {"PENDING": "Ожидает", "COMPLETED": "Завершён", "FAILED": "Ошибка",
        "CANCELLED": "Отменён", "REFUNDED": "Возвращён"}
RU_DRV = {"atol": "АТОЛ", "shtrih": "Штрих-М"}       

def _ru(mapping, key):
    return mapping.get((key or "").strip().upper(), key or "")

def _ru_back(mapping, value):
    for k, v in mapping.items():
        if v == value:
            return k
    return value

def _fio(c):
    f = c.get("fio") or c.get("full_name") or ""
    if not f:
        f = " ".join(x for x in [c.get("last_name"), c.get("first_name"),
                                 c.get("middle_name")] if x)
    return f or c.get("name") or c.get("email") or str(c.get("id"))

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(object)          # передаём само исключение (для _err_text)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(e)

def _err_text(e):
    """Человекочитаемый текст ошибки HTTP из detail ответа сервера."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            detail = resp.json().get("detail")
            if detail:
                return str(detail)
        except Exception:
            pass
        return "Ошибка сервера %s: %s" % (resp.status_code, resp.text[:150])
    return str(e)


def _local(s):
    """UTC-строка от сервера -> локальное время 'YYYY-MM-DD HH:MM'."""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)[:16]

def _money(v):
    try:
        return "%.2f ₽" % float(v or 0)
    except Exception:
        return "0.00 ₽"

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
        # Независимость подвкладок: кнопки платежей блокируются на «Проводках»
        self._pay_action_btns = []
        for text, slot, is_pay_action in [
                ("Обновить", self.reload_all, False),
                ("＋ Провести платёж", self.add_payment, False),
                ("✓ Подтвердить", self.complete_payment, True),
                ("↩ Возврат", self.refund_payment, True),
                ("✕ Отмена платежа", self.cancel_payment, True),
                ("⇩ Экспорт CSV", self.export_csv, False)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
            if is_pay_action:
                self._pay_action_btns.append(b)
        v.addLayout(bar)

        # === Кассовая смена (E31) + балансы (E33) ===
        bar2 = QHBoxLayout()
        self.lbl_shift = QLabel("Смена: —")
        bar2.addWidget(self.lbl_shift)
        b_open = QPushButton("🔓 Открыть смену")
        b_open.setToolTip("Открыть смену на фискальном регистраторе (АТОЛ ДТО)")
        b_open.clicked.connect(lambda: self._shift("open"))
        b_close = QPushButton("🔒 Закрыть смену")
        b_close.setToolTip("Закрыть смену (Z-отчёт): итоги, гашение, остаток в «не снятый»")
        b_close.clicked.connect(lambda: self._shift("close"))
        b_x = QPushButton("📊 X-отчёт")
        b_x.setToolTip("Промежуточный отчёт БЕЗ закрытия смены: итоги нал/безнал. "
                       "Используйте при смене кассиров днём — уходящий снимает X, "
                       "приходящий сверяет деньги, смена продолжается.")
        b_x.clicked.connect(self.x_report)
        b_wd = QPushButton("💵 Снятие кассы")
        b_wd.setToolTip("Бухгалтер снимает остаток прошлых смен (обнуляет)")
        b_wd.clicked.connect(self.cash_withdrawal)
        b_check = QPushButton("Обновить статус")
        b_check.clicked.connect(self._shift_status)
        b_set = QPushButton("⚙ Настройки кассы")
        b_set.setToolTip("Адрес АТОЛ, логин/пароль ДТО, ОФД — вместо ручных команд на сервере")
        b_set.clicked.connect(self.fiscal_settings)
        for b in (b_open, b_close, b_x, b_wd, b_check, b_set):
            bar2.addWidget(b)
        bar2.addStretch(1)
        v.addLayout(bar2)

        self.lbl_bal = QLabel("")
        v.addWidget(self.lbl_bal)
        # ============================================

        hint = QLabel("Отмена = возврат полной суммы (отдельного endpoint "
                      "отмены в API нет). Возврат — полный или частичный. "
                      "Чек пробивается автоматически при «✓ Подтвердить». "
                      "«🔒 Закрыть смену» = Z-отчёт, «📊 X-отчёт» — сверка без закрытия.")
        hint.setStyleSheet("color: #888;")
        v.addWidget(hint)

        self.sub = QTabWidget()
        self.tbl = self._mk_table(self.COLS)
        self.tbl_e = self._mk_table(self.ECOLS)
        self.sub.addTab(self.tbl, "Платежи клиента")
        self.sub.addTab(self.tbl_e, "Проводки (бухгалтерия)")
        self.sub.currentChanged.connect(self._on_sub_changed)
        v.addWidget(self.sub, 1)

        self.cmb_client.currentIndexChanged.connect(lambda _i: self.load_payments())
        self.reload_all()
        self._shift_status()

    def _mk_table(self, cols):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setStyleSheet(_t("table_style"))
        return t

    def _on_sub_changed(self, idx):
        """Независимость подвкладок: кнопки платежей работают только
        на «Платежи клиента», на «Проводках» — неактивны (серые)."""
        for b in getattr(self, "_pay_action_btns", []):
            b.setEnabled(idx == 0)

    # ---------- infra ----------
    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda e: self._show(_err_text(e), ok=False))
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

    # ---------- fiscal shift (E31/E33) ----------
    def _fiscal_url(self, path):
        base = (getattr(self.api, "base_url", "") or "").rstrip("/")
        return base + "/fiscal" + path

    def _shift(self, action):
        def _do():
            r = self.api.session.post(self._fiscal_url("/%s-shift" % action),
                                      timeout=30)
            r.raise_for_status()
            return r.json()
        def _done(res):
            d = res if isinstance(res, dict) else {}
            if action == "close":
                QMessageBox.information(self, "Смена закрыта",
                    "Закрытая смена:\n"
                    "  Наличные: %s\n  Безнал: %s\n\n"
                    "Остаток на кассе (не снят бухгалтером):\n"
                    "  Наличные: %s\n  Безнал: %s"
                    % (_money(d.get("cash_total")), _money(d.get("card_total")),
                       _money(d.get("prev_cash")), _money(d.get("prev_card"))))
            else:
                self._show("Смена открыта.")
            self._shift_status()
        self._run(_do, _done)

    def x_report(self):
        """X-отчёт: итоги смены БЕЗ закрытия (сверка при пересменке)."""
        def _do():
            r = self.api.session.post(self._fiscal_url("/x-report"), timeout=30)
            r.raise_for_status()
            return r.json()
        def _done(d):
            d = d if isinstance(d, dict) else {}
            QMessageBox.information(self, "X-отчёт (без закрытия смены)",
                "Итоги текущей смены:\n"
                "  Наличные: %s\n  Безнал: %s\n\n"
                "Смена остаётся ОТКРЫТОЙ — продажи продолжаются."
                % (_money(d.get("cash_total")), _money(d.get("card_total"))))
            self._shift_status()
        self._run(_do, _done)

    def cash_withdrawal(self):
        if QMessageBox.question(self, "Снятие кассы",
                "Снять весь остаток прошлых смен?\n"
                "(наличные и безналичные обнулятся, операция запишется)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        def _do():
            r = self.api.session.post(self._fiscal_url("/cash-withdrawal"),
                                      timeout=30)
            r.raise_for_status()
            return r.json()
        def _done(d):
            QMessageBox.information(self, "Снятие кассы",
                "Снято:\n  Наличные: %s\n  Безнал: %s"
                % (_money(d.get("withdrawn_cash")), _money(d.get("withdrawn_card"))))
            self._shift_status()
        self._run(_do, _done)

    def fiscal_settings(self):
        """Окно настроек фискального регистратора: читает GET /fiscal/settings,
        сохраняет POST /fiscal/settings. Пустые поля = оставить прежние значения."""
        def _load():
            r = self.api.session.get(self._fiscal_url("/settings"), timeout=15)
            r.raise_for_status()
            return r.json()
        def _ask(cur):
            cur = cur if isinstance(cur, dict) else {}
            st = cur.get("settings") or {}
            ofd = cur.get("ofd_provider") or "ofd-ru"
            self._show("Сейчас: драйвер %s | адрес %s | ОФД %s. "
                       "Пустые поля = без изменений."
                       % (cur.get("driver"), st.get("dto_url") or "—", ofd))
            dlg = FormDialog("Настройки кассы (АТОЛ)", [
                ("driver", "Драйвер", "combo", list(RU_DRV.values())),
                ("dto_url", "Адрес кассы http://IP:порт", "text", None),
                ("dto_login", "Логин ДТО", "text", None),
                ("dto_password", "Пароль ДТО", "text", None),
                ("ofd", "ОФД", "combo", ["ofd-ru", "taxcom", "первый-офд", "yandex"]),
            ], self)
            if not dlg.exec():
                return
            v = dlg.values()
            def _do():
                settings = {
                    "dto_url": (v.get("dto_url") or "").strip() or st.get("dto_url") or "",
                    "dto_login": (v.get("dto_login") or "").strip() or st.get("dto_login") or "",
                    "dto_password": (v.get("dto_password") or "").strip() or st.get("dto_password") or "",
                }
                r = self.api.session.post(self._fiscal_url("/settings"), json={
                    "driver": _ru_back(RU_DRV, v.get("driver") or RU_DRV["atol"]),
                    "port": "TCP",
                    "settings": settings,
                    "ofd_provider": v.get("ofd") or ofd,
                }, timeout=15)
                r.raise_for_status()
                return r.json()
            self._run(_do, lambda _r: self._show("Настройки кассы сохранены."))
        self._run(_load, _ask)

    def _shift_status(self):
        """Тихий опрос: ошибку показываем только в подписи, без баннера."""
        def _do():
            r = self.api.session.get(self._fiscal_url("/shift"), timeout=15)
            r.raise_for_status()
            return r.json()
        def _ok(d):
            open_ = isinstance(d, dict) and bool(d.get("is_open"))
            self.lbl_shift.setText(
                "Смена: открыта ✅" if open_ else "Смена: закрыта ❌")
            if isinstance(d, dict):
                self.lbl_bal.setText(
                    "Текущая смена — нал: %s | безнал: %s  ||  "
                    "Остаток прошлых смен (не снят): нал %s | безнал %s"
                    % (_money(d.get("cash_total")), _money(d.get("card_total")),
                       _money(d.get("prev_cash")), _money(d.get("prev_card"))))
        w = Worker(_do, self)
        w.done.connect(_ok)
        w.fail.connect(lambda _m: (self.lbl_shift.setText(
            "Смена: ? (нет связи)"), self.lbl_bal.setText("")))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w)
                           if w in self._workers else None)
        w.start()

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
        self.sub.setCurrentIndex(0)   # при смене клиента — на «Платежи клиента»
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
                    _local(p.get("created_at") or p.get("payment_date")),
                    str(p.get("amount") or ""),
                    _ru(RU_M, p.get("payment_method") or p.get("method")),
                    _ru(RU_S, p.get("status")),
                    _ru(RU_D, p.get("payment_direction")),
                    _ru(RU_C, p.get("payment_category")),
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
        # Предупреждение при закрытой смене: платёж проведём, но чек не пробьётся
        if "закрыта" in self.lbl_shift.text():
            self._show("Внимание: смена закрыта — фискальный чек не пробьётся, "
                       "пока не нажата «Открыть смену».", ok=False)
        dlg = FormDialog("Провести платёж", [
            ("amount", "Сумма", "text", None),
            ("method", "Способ оплаты", "combo", list(RU_M.values())),
            ("direction", "Направление", "combo", ["Приход", "Расход"]),
            ("category", "Категория", "combo", [""] + list(RU_C.values())),
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
        method = _ru_back(RU_M, v.get("method") or RU_M["CASH"])
        direction = _ru_back(RU_D, v.get("direction")) or None
        category = _ru_back(RU_C, v.get("category")) or None
        self._run(lambda: self.api.create_payment(
            amount, method, client_id=cid,
            notes=v.get("notes") or None,
            direction=direction, category=category),
            lambda _r: (self._show("Платёж проведён."), self.load_payments()))

    def complete_payment(self):
        pid = self._selected_pid()
        if pid is None:
            return
        self._run(lambda: self.api.complete_payment(pid),
                  lambda _r: (self._show("Платёж подтверждён, чек пробит."),
                              self.load_payments(), self._shift_status()))

    def refund_payment(self):
        pid = self._selected_pid()
        if pid is None:
            return
        dlg = FormDialog("Возврат платежа", [
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
                              self.load_payments(), self._shift_status()))

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
                              self.load_payments(), self._shift_status()))

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
        """Проводки: API отдаёт {\"entries\": [...], \"total\": N}; amount одна —
        показываем её в обеих колонках (Дт = Кт по правилу двойной записи)."""
        if isinstance(data, dict):
            rows = data.get("entries") or []
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        self.tbl_e.setRowCount(0)
        for e in rows:
            r = self.tbl_e.rowCount()
            self.tbl_e.insertRow(r)
            amt = e.get("amount")
            amt_s = "%.2f" % float(amt) if amt is not None else ""
            vals = [str(e.get("entry_id") or e.get("id") or "")[:8],
                    str(e.get("entry_date") or e.get("created_at") or "")[:19],
                    e.get("debit_account") or "",
                    e.get("credit_account") or "",
                    amt_s,
                    amt_s,
                    e.get("description") or ""]
            for j, val in enumerate(vals):
                self.tbl_e.setItem(r, j, QTableWidgetItem(str(val)))
        self._show("Проводок: %d" % len(rows))


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