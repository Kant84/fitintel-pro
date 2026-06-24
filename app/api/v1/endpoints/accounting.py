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
