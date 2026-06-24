"""
Путь в проекте: app/api/v1/endpoints/fiscal.py
FastAPI роуты для управления кассами, банками, СБП и рекуррентами.
Подключается в app/api/v1/router.py через:
    router.include_router(fiscal_router, prefix="/fiscal")
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict
from pydantic import BaseModel

from app.services.fiscal.universal_fiscal import (
    FiscalManager, CheckItem, PaymentTypeEnum, AtolAdapter, ShtrihAdapter, EvotorAdapter, MercuryAdapter
)
from app.services.bank.universal_bank import BankManager
from app.services.sbp_service import SbpAndSubscriptionManager

fiscal_router = APIRouter(prefix="/fiscal", tags=["fiscal"])

# Конфигурация (в продакшене — из БД настроек клуба)
FISCAL_CONFIG = {
    "active": "atol",
    "atol": {"base_url": "http://127.0.0.1:16732"},
    "shtrih": {"base_url": "http://127.0.0.1:8080", "password": "30"},
    "evotor": {"token": ""},
    "mercury": {"base_url": "http://127.0.0.1:5000", "api_key": ""}
}

BANK_CONFIG = {
    "active": "tinkoff",
    "sber": {"mode": "mock"},
    "tinkoff": {"terminal_key": "", "password": ""},
    "raiff": {"merchant_id": "", "key": ""}
}

_sbp = SbpAndSubscriptionManager(mock=True)


class CheckItemRequest(BaseModel):
    name: str
    price: float
    quantity: float = 1.0
    payment_method: str = "fullPrepayment"
    payment_object: str = "service"
    tax_type: str = "none"


class PrintCheckRequest(BaseModel):
    items: List[CheckItemRequest]
    payment_type: str = "electronic"
    total: Optional[float] = None
    slip: str = ""
    operator_name: str = "Администратор"


class SbpQrRequest(BaseModel):
    amount: float
    order_id: Optional[str] = None


class RebillRequest(BaseModel):
    client_id: int


class ChargeRequest(BaseModel):
    amount: float
    rebill_id: str


# =========================================================================
# КАССЫ
# =========================================================================
@fiscal_router.get("/printers")
def list_printers():
    """Список доступных касс."""
    mgr = FiscalManager(FISCAL_CONFIG)
    return {"available": mgr.list_available(), "active": FISCAL_CONFIG.get("active")}


@fiscal_router.post("/printers/switch/{printer_key}")
def switch_printer(printer_key: str, settings: Optional[dict] = None):
    """Переключить активную кассу."""
    mgr = FiscalManager(FISCAL_CONFIG)
    try:
        mgr.switch(printer_key, **(settings or {}))
        return {"success": True, "active": printer_key}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@fiscal_router.get("/printers/health")
def health_all():
    """Проверить все настроенные кассы."""
    mgr = FiscalManager(FISCAL_CONFIG)
    return mgr.health_check_all()


@fiscal_router.post("/printers/open-shift")
def open_shift(operator_name: str = "Администратор"):
    """Открыть смену на активной кассе."""
    mgr = FiscalManager(FISCAL_CONFIG)
    res = mgr.printer.open_shift(operator_name)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка кассы"))
    return res


@fiscal_router.post("/printers/sale-check")
def print_sale_check(req: PrintCheckRequest):
    """Пробить чек прихода."""
    mgr = FiscalManager(FISCAL_CONFIG)
    items = [CheckItem(
        name=i.name, price=i.price, quantity=i.quantity,
        payment_method=i.payment_method, payment_object=i.payment_object, tax_type=i.tax_type
    ) for i in req.items]
    pt = PaymentTypeEnum(req.payment_type) if req.payment_type in [e.value for e in PaymentTypeEnum] else PaymentTypeEnum.ELECTRONIC
    res = mgr.printer.print_sale_check(items, pt, req.total, req.slip)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка кассы"))
    return res


@fiscal_router.post("/printers/return-check")
def print_return_check(req: PrintCheckRequest):
    """Пробить чек возврата."""
    mgr = FiscalManager(FISCAL_CONFIG)
    items = [CheckItem(
        name=i.name, price=i.price, quantity=i.quantity,
        payment_method=i.payment_method, payment_object=i.payment_object, tax_type=i.tax_type
    ) for i in req.items]
    pt = PaymentTypeEnum(req.payment_type) if req.payment_type in [e.value for e in PaymentTypeEnum] else PaymentTypeEnum.ELECTRONIC
    res = mgr.printer.print_return_check(items, pt, req.total, req.slip)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка кассы"))
    return res


@fiscal_router.post("/printers/close-shift")
def close_shift(operator_name: str = "Администратор"):
    """Закрыть смену (Z-отчет)."""
    mgr = FiscalManager(FISCAL_CONFIG)
    res = mgr.printer.close_shift(operator_name)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка кассы"))
    return res


@fiscal_router.post("/printers/cancel-last")
def cancel_last_document():
    """Аннулировать последний документ."""
    mgr = FiscalManager(FISCAL_CONFIG)
    res = mgr.printer.cancel_last_document()
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка кассы"))
    return res


@fiscal_router.get("/printers/status")
def printer_status():
    """Статус активной кассы."""
    mgr = FiscalManager(FISCAL_CONFIG)
    return mgr.printer.get_status()


# =========================================================================
# БАНКИ / ЭКВАЙРИНГ
# =========================================================================
@fiscal_router.get("/banks")
def list_banks():
    """Список доступных банков."""
    mgr = BankManager(BANK_CONFIG)
    return {"available": mgr.list_available(), "active": BANK_CONFIG.get("active")}


@fiscal_router.post("/banks/switch/{bank_key}")
def switch_bank(bank_key: str, settings: Optional[dict] = None):
    """Переключить активный банк."""
    mgr = BankManager(BANK_CONFIG)
    try:
        mgr.switch(bank_key, **(settings or {}))
        return {"success": True, "active": bank_key}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@fiscal_router.post("/banks/pay")
def bank_pay(amount: float, order_id: Optional[str] = None):
    """Оплата через активный банковский терминал."""
    mgr = BankManager(BANK_CONFIG)
    res = mgr.terminal.pay(amount, order_id)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка банка"))
    return res


@fiscal_router.post("/banks/cancel")
def bank_cancel(rrn: Optional[str] = None, amount: Optional[float] = None):
    """Отмена/возврат последней операции."""
    mgr = BankManager(BANK_CONFIG)
    res = mgr.terminal.cancel_last(rrn, amount)
    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Ошибка банка"))
    return res


@fiscal_router.post("/banks/settlement")
def bank_settlement():
    """Сверка итогов банка."""
    mgr = BankManager(BANK_CONFIG)
    return mgr.terminal.settlement()


@fiscal_router.get("/banks/status")
def bank_status():
    """Статус банковского терминала."""
    mgr = BankManager(BANK_CONFIG)
    return mgr.terminal.get_status()


# =========================================================================
# СБП / РЕКУРРЕНТЫ
# =========================================================================
@fiscal_router.post("/sbp/qr")
def sbp_qr(req: SbpQrRequest):
    """Сгенерировать QR-код для СБП."""
    qr = _sbp.generate_dynamic_qr(req.amount, req.order_id or f"sbp_{int(__import__('time').time())}")
    return {"success": True, "qr_url": qr["qr_url"], "payment_id": qr["payment_id"]}


@fiscal_router.get("/sbp/status/{order_id}")
def sbp_status(order_id: str):
    """Проверить статус оплаты по СБП."""
    paid = _sbp.check_qr_payment_status(order_id)
    return {"success": True, "paid": paid}


@fiscal_router.post("/subscription/register")
def register_autopay(req: RebillRequest):
    """Привязать карту клиента для рекуррентов."""
    token = _sbp.register_autopay_token(req.client_id)
    return {"success": True, "rebill_id": token}


@fiscal_router.post("/subscription/charge")
def charge_subscription(req: ChargeRequest):
    """Списать абонемент по токену рекуррентов."""
    ok = _sbp.charge_subscription(req.amount, req.rebill_id)
    return {"success": ok}
