"""
Путь в проекте: app/api/v1/endpoints/accounting.py
FastAPI роуты для внутренней бухгалтерии и интеграции с 1С.
Подключается в app/api/v1/router.py через:
    router.include_router(accounting_router, prefix="/accounting")
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional, List
from pydantic import BaseModel

from app.services.accounting.internal_accounting import InternalAccounting
from app.services.accounting.onec_integration import OneCIntegration

accounting_router = APIRouter(prefix="/accounting", tags=["accounting"])

_acc = InternalAccounting()
_onec = OneCIntegration(mode="mock")


class PkoRequest(BaseModel):
    amount: float
    contragent_id: Optional[str] = None
    description: str = ""
    doc_number: Optional[str] = None


class RkoRequest(BaseModel):
    amount: float
    expense_account: str = "91.2"
    description: str = ""
    doc_number: Optional[str] = None


class SaleRequest(BaseModel):
    amount: float
    contragent_id: Optional[str] = None
    item_id: Optional[str] = None
    description: str = ""
    doc_number: Optional[str] = None
    payment_type: str = "cash"


class PurchaseRequest(BaseModel):
    amount: float
    supplier_id: str
    description: str = ""
    doc_number: Optional[str] = None


class ManualEntryRequest(BaseModel):
    debit: str
    credit: str
    amount: float
    description: str = ""
    doc_number: Optional[str] = None


class ContragentRequest(BaseModel):
    name: str
    type: str = "client"
    inn: str = ""
    full_name: str = ""
    phone: str = ""
    email: str = ""


class ItemRequest(BaseModel):
    name: str
    type: str = "service"
    price: float = 0.0
    cost_price: float = 0.0
    unit: str = "шт"
    vat_rate: float = 0.0


# =========================================================================
# ВНУТРЕННЯЯ БУХГАЛТЕРИЯ
# =========================================================================
@accounting_router.post("/pko")
def create_pko(req: PkoRequest):
    """Приходный кассовый ордер."""
    eid = _acc.create_pko(req.amount, req.contragent_id, req.description, req.doc_number)
    return {"success": True, "entry_id": eid}


@accounting_router.post("/rko")
def create_rko(req: RkoRequest):
    """Расходный кассовый ордер."""
    eid = _acc.create_rko(req.amount, req.expense_account, req.description, req.doc_number)
    return {"success": True, "entry_id": eid}


@accounting_router.post("/sale")
def create_sale(req: SaleRequest):
    """Реализация услуги (абонемент)."""
    eid = _acc.create_sale(req.amount, req.contragent_id, req.item_id, req.description, req.doc_number, req.payment_type)
    return {"success": True, "entry_id": eid}


@accounting_router.post("/purchase")
def create_purchase(req: PurchaseRequest):
    """Поступление от поставщика."""
    eid = _acc.create_purchase(req.amount, req.supplier_id, req.description, req.doc_number)
    return {"success": True, "entry_id": eid}


@accounting_router.post("/manual-entry")
def create_manual_entry(req: ManualEntryRequest):
    """Ручная бухгалтерская проводка."""
    eid = _acc.create_manual_entry(req.debit, req.credit, req.amount, req.description, req.doc_number)
    return {"success": True, "entry_id": eid}


@accounting_router.post("/contragents")
def add_contragent(req: ContragentRequest):
    """Добавить контрагента."""
    cid = _acc.add_contragent(req.name, req.type, req.inn, req.full_name, req.phone, req.email)
    return {"success": True, "contragent_id": cid}


@accounting_router.post("/items")
def add_item(req: ItemRequest):
    """Добавить номенклатуру."""
    iid = _acc.add_item(req.name, req.type, req.price, req.cost_price, req.unit, req.vat_rate)
    return {"success": True, "item_id": iid}


# =========================================================================
# ОТЧЕТЫ
# =========================================================================
@accounting_router.get("/osv/{period}")
def osv(period: str, account: Optional[str] = None):
    """Оборотно-сальдовая ведомость. period = YYYY-MM."""
    return _acc.osv(period, account)


@accounting_router.get("/turnover/{account}/{period}")
def turnover(account: str, period: str):
    """Оборотка по счету."""
    return _acc.turnover_by_account(account, period)


@accounting_router.get("/profit-loss/{period}")
def profit_loss(period: str):
    """Отчет о прибылях и убытках."""
    return _acc.profit_loss(period)


@accounting_router.get("/balance-sheet/{period}")
def balance_sheet(period: str):
    """Упрощенный баланс."""
    return _acc.balance_sheet(period)


@accounting_router.get("/cash-flow/{period}")
def cash_flow(period: str):
    """Движение денежных средств."""
    return _acc.cash_flow(period)


@accounting_router.get("/contragents/{contragent_id}/balance")
def contragent_balance(contragent_id: str):
    """Баланс по контрагенту."""
    return {"contragent_id": contragent_id, "balance": _acc.contragent_balance(contragent_id)}


@accounting_router.get("/contragents/{contragent_id}/reconciliation/{period}")
def reconciliation_act(contragent_id: str, period: str):
    """Акт сверки взаиморасчетов."""
    return _acc.reconciliation_act(contragent_id, period)


# =========================================================================
# 1С ИНТЕГРАЦИЯ
# =========================================================================
@accounting_router.post("/1c/export-catalog")
def export_catalog(items: List[dict]):
    """Выгрузить номенклатуру в 1С (CommerceML)."""
    path = _onec.export_catalog(items)
    return {"success": True, "file": path}


@accounting_router.post("/1c/export-contragents")
def export_contragents(clients: List[dict]):
    """Выгрузить контрагентов в 1С."""
    path = _onec.export_contragents(clients)
    return {"success": True, "file": path}


@accounting_router.post("/1c/export-documents")
def export_documents(docs: List[dict]):
    """Выгрузить документы в 1С."""
    path = _onec.export_documents(docs)
    return {"success": True, "file": path}


@accounting_router.post("/1c/import-offers")
def import_offers(file_path: str):
    """Импортировать цены/остатки из 1С (offers.xml)."""
    offers = _onec.import_offers(file_path)
    return {"success": True, "offers": offers}


@accounting_router.post("/1c/import-orders")
def import_orders(file_path: str):
    """Импортировать заказы из 1С."""
    orders = _onec.import_orders_from_1c(file_path)
    return {"success": True, "orders": orders}


@accounting_router.get("/1c/exchange-files")
def list_exchange_files():
    """Список файлов обмена с 1С."""
    return {"files": _onec.list_exchange_files()}

# ==================== E32: проводки, баланс, отчёты, обмен 1С ====================
import calendar as _calendar
import uuid as _uuid
import xml.etree.ElementTree as _ET
from datetime import date as _date, datetime as _dt, timezone as _tz
from xml.sax.saxutils import escape as _xesc

from fastapi import Depends as _Depends, Response as _Response
from sqlalchemy import text as _text
from sqlalchemy.orm import Session as _Session

from app.api.dependencies import get_current_user as _gcu
from app.db.session import get_db as _gdb


class _EntryCreate(BaseModel):
    debit_account: str
    credit_account: str
    debit: float
    credit: float
    description: str = ""
    entry_date: Optional[str] = None
    source: str = "manual"


class _EntryUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None


class _AutoDoc(BaseModel):
    amount: float
    doc_id: Optional[str] = None
    description: str = ""


def _e32_insert(db, table, data):
    rows = db.execute(_text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    cols = {r[0] for r in rows}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(_text(
        f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"
    ), data)


def _e32_new_entry(db, debit_account, credit_account, amount, description="",
                   source="manual", source_id=None, entry_date=None, is_closing=False):
    eid = str(_uuid.uuid4())
    now = _dt.now(_tz.utc)
    _e32_insert(db, "accounting_entries", {
        "id": eid, "entry_date": entry_date or _date.today().isoformat(),
        "debit_account": debit_account, "credit_account": credit_account,
        "amount": amount, "description": description, "source": source,
        "source_id": source_id, "is_closing": is_closing,
        "created_at": now, "updated_at": now,
    })
    return eid


_E32_COLS = "id, entry_date, debit_account, credit_account, amount, description, source, is_closing"


def _e32_row(r):
    return {"entry_id": r[0], "entry_date": r[1], "debit_account": r[2],
            "credit_account": r[3], "amount": float(r[4] or 0), "description": r[5],
            "source": r[6], "is_closing": bool(r[7])}


def _e32_query(db, date_from, date_to):
    q = f"SELECT {_E32_COLS} FROM accounting_entries WHERE 1=1"
    params = {}
    if date_from:
        q += " AND entry_date >= :df"
        params["df"] = date_from
    if date_to:
        q += " AND entry_date <= :dt"
        params["dt"] = date_to
    q += " ORDER BY entry_date, created_at"
    return db.execute(_text(q), params).fetchall()


@accounting_router.post("/entries", status_code=201)
def e32_create_entry(payload: _EntryCreate, db: _Session = _Depends(_gdb),
                     user=_Depends(_gcu)):
    """E32.1/E32.2 — создание проводки с валидацией баланса"""
    if round(payload.debit, 2) != round(payload.credit, 2):
        raise HTTPException(status_code=400, detail="Дебет и кредит не равны")
    eid = _e32_new_entry(db, payload.debit_account, payload.credit_account,
                         payload.debit, payload.description, payload.source,
                         entry_date=payload.entry_date)
    db.commit()
    return {"entry_id": eid, "message": "Проводка создана",
            "debit_account": payload.debit_account,
            "credit_account": payload.credit_account, "amount": payload.debit}


@accounting_router.get("/entries")
def e32_list_entries(date_from: Optional[str] = None, date_to: Optional[str] = None,
                     db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.3 — список проводок за период"""
    rows = _e32_query(db, date_from, date_to)
    entries = [_e32_row(r) for r in rows]
    return {"entries": entries, "total": len(entries)}


@accounting_router.get("/entries/{entry_id}")
def e32_get_entry(entry_id: str, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.4 — проводка по ID"""
    r = db.execute(_text(
        f"SELECT {_E32_COLS} FROM accounting_entries WHERE id = :id"
    ), {"id": entry_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Проводка не найдена")
    return _e32_row(r)


@accounting_router.put("/entries/{entry_id}")
def e32_update_entry(entry_id: str, payload: _EntryUpdate,
                     db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.5 — обновление проводки"""
    r = db.execute(_text("SELECT id FROM accounting_entries WHERE id = :id"),
                   {"id": entry_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Проводка не найдена")
    now = _dt.now(_tz.utc)
    if payload.description is not None:
        db.execute(_text(
            "UPDATE accounting_entries SET description = :d, updated_at = :u WHERE id = :id"
        ), {"d": payload.description, "u": now, "id": entry_id})
    if payload.amount is not None:
        db.execute(_text(
            "UPDATE accounting_entries SET amount = :a, updated_at = :u WHERE id = :id"
        ), {"a": payload.amount, "u": now, "id": entry_id})
    db.commit()
    return {"entry_id": entry_id, "message": "Проводка обновлена"}


@accounting_router.delete("/entries/{entry_id}", status_code=204)
def e32_delete_entry(entry_id: str, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.6 — удаление проводки"""
    r = db.execute(_text(
        "DELETE FROM accounting_entries WHERE id = :id RETURNING id"
    ), {"id": entry_id}).fetchone()
    db.commit()
    if not r:
        raise HTTPException(status_code=404, detail="Проводка не найдена")
    return _Response(status_code=204)


@accounting_router.get("/balance")
def e32_balance(account: str, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.7 — баланс по счёту"""
    d = db.execute(_text(
        "SELECT COALESCE(SUM(amount), 0) FROM accounting_entries WHERE debit_account = :a"
    ), {"a": account}).scalar()
    c = db.execute(_text(
        "SELECT COALESCE(SUM(amount), 0) FROM accounting_entries WHERE credit_account = :a"
    ), {"a": account}).scalar()
    return {"account": account, "balance": float(d) - float(c),
            "debit_total": float(d), "credit_total": float(c)}


@accounting_router.get("/turnover")
def e32_turnover(date_from: Optional[str] = None, date_to: Optional[str] = None,
                 db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.8 — оборотно-сальдовая ведомость"""
    df = date_from or "0000-01-01"
    dt = date_to or "9999-12-31"
    rows = db.execute(_text(
        "SELECT account, SUM(d), SUM(c) FROM ("
        "  SELECT debit_account AS account, SUM(amount) AS d, 0.0 AS c"
        "  FROM accounting_entries WHERE entry_date BETWEEN :df AND :dt GROUP BY debit_account"
        "  UNION ALL"
        "  SELECT credit_account, 0.0, SUM(amount)"
        "  FROM accounting_entries WHERE entry_date BETWEEN :df AND :dt GROUP BY credit_account"
        ") t GROUP BY account ORDER BY account"
    ), {"df": df, "dt": dt}).fetchall()
    turnover = [{"account": r[0], "debit_turnover": float(r[1] or 0),
                 "credit_turnover": float(r[2] or 0),
                 "balance": float(r[1] or 0) - float(r[2] or 0)} for r in rows]
    return {"date_from": df, "date_to": dt, "turnover": turnover}


@accounting_router.get("/general-ledger")
def e32_general_ledger(date_from: Optional[str] = None, date_to: Optional[str] = None,
                       db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.9 — главная книга"""
    return e32_list_entries(date_from, date_to, db, user)

@accounting_router.get("/export/1c")
def e32_export_1c(date_from: Optional[str] = None, date_to: Optional[str] = None,
                  db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.10 — экспорт проводок в XML для 1С"""
    rows = _e32_query(db, date_from, date_to)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<entries>"]
    for r in rows:
        lines.append(
            f'  <entry date="{r[1]}" debit="{_xesc(str(r[2]))}" credit="{_xesc(str(r[3]))}" '
            f'amount="{float(r[4] or 0)}" source="{_xesc(str(r[6] or "manual"))}">'
            f'<description>{_xesc(str(r[5] or ""))}</description></entry>'
        )
    lines.append("</entries>")
    return _Response(content="\n".join(lines), media_type="application/xml")


@accounting_router.get("/export/buh")
def e32_export_buh(date_from: Optional[str] = None, date_to: Optional[str] = None,
                   db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.11 — экспорт в файл для Бухгалтерии (CSV)"""
    rows = _e32_query(db, date_from, date_to)
    lines = ["date;debit_account;credit_account;amount;description"]
    for r in rows:
        desc = str(r[5] or "").replace(";", ",")
        lines.append(f"{r[1]};{r[2]};{r[3]};{float(r[4] or 0)};{desc}")
    return _Response(content="\n".join(lines), media_type="text/csv")


@accounting_router.post("/import/1c")
async def e32_import_1c(file: UploadFile = File(...), db: _Session = _Depends(_gdb),
                        user=_Depends(_gcu)):
    """E32.12 — импорт проводок из XML 1С"""
    content = (await file.read()).decode("utf-8")
    root = _ET.fromstring(content)
    imported = 0
    for e in root.iter("entry"):
        desc_el = e.find("description")
        _e32_new_entry(
            db, e.get("debit", "unknown"), e.get("credit", "unknown"),
            float(e.get("amount", 0) or 0),
            desc_el.text if desc_el is not None and desc_el.text else "",
            e.get("source", "1c-import"), entry_date=e.get("date"),
        )
        imported += 1
    db.commit()
    return {"message": "Проводки импортированы", "imported": imported}


@accounting_router.post("/auto/from-sale", status_code=201)
def e32_auto_from_sale(payload: _AutoDoc, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.13 — автопроводка от продажи: Дт Касса — Кт Выручка"""
    eid = _e32_new_entry(db, "cash", "revenue", payload.amount,
                         payload.description or "Автопроводка от продажи",
                         "sale", payload.doc_id)
    db.commit()
    return {"entry_id": eid, "debit_account": "cash", "credit_account": "revenue",
            "amount": payload.amount, "message": "Проводка создана автоматически"}


@accounting_router.post("/auto/from-payment", status_code=201)
def e32_auto_from_payment(payload: _AutoDoc, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.14 — автопроводка от платежа: Дт Банк — Кт Дебиторская задолженность"""
    eid = _e32_new_entry(db, "bank", "receivables", payload.amount,
                         payload.description or "Автопроводка от платежа",
                         "payment", payload.doc_id)
    db.commit()
    return {"entry_id": eid, "debit_account": "bank", "credit_account": "receivables",
            "amount": payload.amount, "message": "Проводка создана автоматически"}


@accounting_router.post("/close-month")
def e32_close_month(year: int, month: int, db: _Session = _Depends(_gdb), user=_Depends(_gcu)):
    """E32.15 — закрытие месяца (проводки закрытия + фиксация периода)"""
    row = db.execute(_text(
        "SELECT id FROM accounting_periods WHERE year = :y AND month = :m"
    ), {"y": year, "m": month}).fetchone()
    if row:
        return {"message": "Месяц уже закрыт", "closing_entries": [],
                "year": year, "month": month}
    last = _calendar.monthrange(year, month)[1]
    df = f"{year:04d}-{month:02d}-01"
    dt_ = f"{year:04d}-{month:02d}-{last:02d}"
    revenue = float(db.execute(_text(
        "SELECT COALESCE(SUM(amount), 0) FROM accounting_entries "
        "WHERE credit_account = 'revenue' AND entry_date BETWEEN :df AND :dt"
    ), {"df": df, "dt": dt_}).scalar())
    expense = float(db.execute(_text(
        "SELECT COALESCE(SUM(amount), 0) FROM accounting_entries "
        "WHERE debit_account = 'expense' AND entry_date BETWEEN :df AND :dt"
    ), {"df": df, "dt": dt_}).scalar())
    closing = []
    if revenue > 0:
        closing.append(_e32_new_entry(db, "revenue", "profit", revenue,
                                      f"Закрытие выручки за {month:02d}.{year}",
                                      "closing", entry_date=dt_, is_closing=True))
    if expense > 0:
        closing.append(_e32_new_entry(db, "profit", "expense", expense,
                                      f"Закрытие расходов за {month:02d}.{year}",
                                      "closing", entry_date=dt_, is_closing=True))
    now = _dt.now(_tz.utc)
    _e32_insert(db, "accounting_periods",
                {"id": str(_uuid.uuid4()), "year": year, "month": month,
                 "closed_at": now, "created_at": now})
    db.commit()
    return {"message": "Месяц закрыт", "closing_entries": closing,
            "entries_created": len(closing), "year": year, "month": month}
