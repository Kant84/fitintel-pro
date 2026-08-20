# app/api/v1/fiscal.py
"""
Fiscal API E31 — фискализация чеков (АТОЛ / Штрих-М), возвраты, корректировки,
ОФД (в т.ч. Taxcom), настройки ФР, X/Z-отчёты, смены.
Драйверы эмулируются; боевые — через app/services/fiscal/universal_fiscal.py.
"""

import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db

router = APIRouter(prefix="/fiscal", tags=["Fiscal E31"])

# Эмуляция подключения драйверов ФР (для E31.2)
_DRIVERS = {"atol": True, "shtrih": True}


def _insert(db: Session, table: str, data: dict):
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    cols = {r[0] for r in rows}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(text(f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"), data)


def _fn() -> str:
    return f"{secrets.randbelow(10**10):010d}"


def _sign() -> str:
    return f"{secrets.randbelow(10**10):010d}"


def _get_settings(db: Session) -> dict:
    row = db.execute(text(
        "SELECT driver, port, settings, ofd_provider FROM fiscal_settings ORDER BY created_at LIMIT 1"
    )).fetchone()
    if not row:
        return {"driver": "atol", "port": "COM3", "settings": {}, "ofd_provider": "ofd-ru"}
    try:
        extra = json.loads(row[2]) if row[2] else {}
    except Exception:
        extra = {}
    return {"driver": row[0], "port": row[1], "settings": extra, "ofd_provider": row[3]}


def _get_shift(db: Session):
    return db.execute(text(
        "SELECT id, is_open FROM fiscal_shift ORDER BY created_at LIMIT 1"
    )).fetchone()


def _check_driver(name: str):
    if not _DRIVERS.get(name, False):
        raise HTTPException(status_code=503, detail=f"{'АТОЛ' if name == 'atol' else 'Штрих-М'} недоступен")


def _fiscalize(db: Session, driver: str, receipt_type: str, amount: float,
               receipt_id: Optional[str] = None, original_receipt_id: Optional[str] = None,
               payload: Optional[dict] = None) -> dict:
    """Общая фискализация: создаёт чек, возвращает данные"""
    if receipt_id:
        exists = db.execute(text(
            "SELECT 1 FROM fiscal_receipts WHERE receipt_id = :r"
        ), {"r": receipt_id}).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="Чек уже фискализирован")
    else:
        receipt_id = f"rc-{uuid.uuid4().hex[:12]}"

    settings = _get_settings(db)
    fn, sign = _fn(), _sign()
    now = datetime.now(timezone.utc)
    _insert(db, "fiscal_receipts", {
        "id": str(uuid.uuid4()), "receipt_id": receipt_id, "driver": driver,
        "receipt_type": receipt_type, "amount": amount, "status": "delivered",
        "fiscal_document_number": fn, "fiscal_document_sign": sign,
        "original_receipt_id": original_receipt_id,
        "ofd_provider": settings["ofd_provider"],
        "payload": json.dumps(payload or {}, ensure_ascii=False),
        "created_at": now, "updated_at": now,
    })
    db.commit()
    return {
        "receipt_id": receipt_id, "driver": driver, "receipt_type": receipt_type,
        "status": "delivered",
        "fiscal_document_number": fn, "fiscal_document_sign": sign,
        "ofd_provider": settings["ofd_provider"], "ofd_delivered": True,
        "message": "Чек фискализирован",
    }


class FiscalizeRequest(BaseModel):
    receipt_id: Optional[str] = None
    receipt_data: dict = {}


class RefundRequest(BaseModel):
    original_receipt_id: str
    amount: Optional[float] = None


class CorrectionRequest(BaseModel):
    original_receipt_id: str
    correction_data: dict = {}


class FiscalSettingsRequest(BaseModel):
    driver: str = "atol"
    port: str = "COM3"
    settings: dict = {}
    ofd_provider: Optional[str] = None


class DriversRequest(BaseModel):
    atol: Optional[bool] = None
    shtrih: Optional[bool] = None


@router.post("/atol")
def fiscalize_atol(payload: FiscalizeRequest, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """E31.1/E31.2/E31.5/E31.15 — фискализация через АТОЛ"""
    _check_driver("atol")
    amount = float(payload.receipt_data.get("amount", 0) or 0)
    return _fiscalize(db, "atol", "sale", amount, payload.receipt_id,
                      payload=payload.receipt_data)


@router.post("/shtrih")
def fiscalize_shtrih(payload: FiscalizeRequest, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    """E31.3 — фискализация через Штрих-М"""
    _check_driver("shtrih")
    amount = float(payload.receipt_data.get("amount", 0) or 0)
    return _fiscalize(db, "shtrih", "sale", amount, payload.receipt_id,
                      payload=payload.receipt_data)


@router.get("/status")
def fiscal_status(receipt_id: str, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    """E31.4 — статус фискализации"""
    row = db.execute(text(
        "SELECT status, fiscal_document_number, driver, receipt_type FROM fiscal_receipts "
        "WHERE receipt_id = :r"
    ), {"r": receipt_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Чек не найден")
    return {"receipt_id": receipt_id, "status": row[0],
            "fiscal_document_number": row[1], "driver": row[2], "receipt_type": row[3]}


@router.post("/refund")
def fiscal_refund(payload: RefundRequest, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    """E31.6 — возвратный фискальный чек"""
    orig = db.execute(text(
        "SELECT amount FROM fiscal_receipts WHERE receipt_id = :r AND receipt_type = 'sale'"
    ), {"r": payload.original_receipt_id}).fetchone()
    if not orig:
        raise HTTPException(status_code=404, detail="Оригинальный чек не найден")
    result = _fiscalize(db, _get_settings(db)["driver"], "refund",
                        payload.amount if payload.amount is not None else float(orig[0]),
                        original_receipt_id=payload.original_receipt_id)
    result["refund_fiscal_document_number"] = result["fiscal_document_number"]
    return result


@router.post("/correction")
def fiscal_correction(payload: CorrectionRequest, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    """E31.7 — корректировочный фискальный чек"""
    orig = db.execute(text(
        "SELECT 1 FROM fiscal_receipts WHERE receipt_id = :r"
    ), {"r": payload.original_receipt_id}).fetchone()
    if not orig:
        raise HTTPException(status_code=404, detail="Оригинальный чек не найден")
    result = _fiscalize(db, _get_settings(db)["driver"], "correction", 0,
                        original_receipt_id=payload.original_receipt_id,
                        payload=payload.correction_data)
    result["correction_fiscal_document_number"] = result["fiscal_document_number"]
    return result
# ---------- Настройки ФР (E31.9, E31.10, E31.15) ----------

@router.post("/settings")
def set_settings(payload: FiscalSettingsRequest, db: Session = Depends(get_db),
                 user=Depends(require_roles("admin"))):
    """E31.9 — настройка фискального регистратора"""
    now = datetime.now(timezone.utc)
    row = db.execute(text(
        "SELECT id FROM fiscal_settings ORDER BY created_at LIMIT 1"
    )).fetchone()
    ofd = payload.ofd_provider or "ofd-ru"
    settings_json = json.dumps(payload.settings or {}, ensure_ascii=False)
    if row:
        db.execute(text(
            "UPDATE fiscal_settings SET driver = :d, port = :p, settings = :s, ofd_provider = :o WHERE id = :id"
        ), {"d": payload.driver, "p": payload.port, "s": settings_json, "o": ofd, "id": row[0]})
    else:
        _insert(db, "fiscal_settings", {
            "id": str(uuid.uuid4()), "driver": payload.driver, "port": payload.port,
            "settings": settings_json, "ofd_provider": ofd,
            "created_at": now, "updated_at": now,
        })
    db.commit()
    return {"message": "ФР настроен", "driver": payload.driver,
            "port": payload.port, "ofd_provider": ofd}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.10 — текущие настройки ФР"""
    return _get_settings(db)


# ---------- ОФД (E31.8) ----------

@router.get("/ofd-check")
def ofd_check(fiscal_number: str, db: Session = Depends(get_db),
              user=Depends(get_current_user)):
    """E31.8 — проверка чека в ОФД по фискальному номеру"""
    row = db.execute(text(
        "SELECT ofd_provider FROM fiscal_receipts WHERE fiscal_document_number = :fn"
    ), {"fn": fiscal_number}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Чек не найден")
    provider = row[0] or "ofd-ru"
    return {"fiscal_number": fiscal_number, "ofd_status": "delivered",
            "ofd_provider": provider,
            "ofd_url": f"https://{provider}.example.ru/receipt/{fiscal_number}"}


# ---------- Смены (E31.13, E31.14) ----------

def _set_shift(db: Session, is_open: bool):
    now = datetime.now(timezone.utc)
    row = _get_shift(db)
    if row:
        db.execute(text("UPDATE fiscal_shift SET is_open = :o WHERE id = :id"),
                   {"o": is_open, "id": row[0]})
    else:
        _insert(db, "fiscal_shift", {"id": str(uuid.uuid4()), "is_open": is_open,
                                     "created_at": now, "updated_at": now})
    db.commit()


@router.post("/open-shift")
def open_shift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.13 — открытие смены"""
    row = _get_shift(db)
    if row and row[1]:
        raise HTTPException(status_code=400, detail="Смена уже открыта")
    _set_shift(db, True)
    return {"shift_open": True, "message": "Смена открыта"}


@router.post("/close-shift")
def close_shift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.14 — закрытие смены (идемпотентно)"""
    _set_shift(db, False)
    return {"shift_open": False, "message": "Смена закрыта"}


# ---------- Отчёты (E31.11, E31.12) ----------

@router.post("/x-report")
def x_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.11 — X-отчёт без закрытия смены"""
    row = _get_shift(db)
    if not row or not row[1]:
        raise HTTPException(status_code=400, detail="Смена не открыта")
    total = db.execute(text(
        "SELECT COALESCE(SUM(amount), 0) FROM fiscal_receipts WHERE receipt_type = 'sale'"
    )).scalar()
    return {"printed": True, "report_type": "X", "total": float(total),
            "shift_open": True, "message": "X-отчёт напечатан"}


@router.post("/z-report")
def z_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.12 — Z-отчёт с закрытием смены"""
    row = _get_shift(db)
    if not row or not row[1]:
        raise HTTPException(status_code=400, detail="Смена не открыта")
    total = db.execute(text(
        "SELECT COALESCE(SUM(amount), 0) FROM fiscal_receipts WHERE receipt_type = 'sale'"
    )).scalar()
    _set_shift(db, False)
    return {"printed": True, "report_type": "Z", "total": float(total),
            "shift_closed": True, "shift_open": False,
            "message": "Z-отчёт напечатан, смена закрыта"}


# ---------- Тестовый переключатель драйверов (E31.2) ----------

@router.post("/test/drivers")
def test_drivers(payload: DriversRequest, user=Depends(get_current_user)):
    """Эмуляция доступности драйверов ФР (только для тестов!)"""
    if payload.atol is not None:
        _DRIVERS["atol"] = payload.atol
    if payload.shtrih is not None:
        _DRIVERS["shtrih"] = payload.shtrih
    return {"drivers": _DRIVERS}
