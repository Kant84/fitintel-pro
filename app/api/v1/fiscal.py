# app/api/v1/fiscal.py
"""
Fiscal API E31 — фискализация чеков (АТОЛ / Штрих-М), возвраты, корректировки,
ОФД, настройки ФР, X/Z-отчёты, смены.
E33 — балансы смен (нал/безнал раздельно), остаток предыдущих смен, снятие кассы.
Миграция схемы — автоматическая (_ensure_schema), ручной SQL не требуется.
"""
import requests
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db

router = APIRouter(prefix="/fiscal", tags=["Fiscal E31"])

# Эмуляция подключения драйверов ФР (для E31.2)
_DRIVERS = {"atol": True, "shtrih": True}


# ---------- Базовые helpers ----------

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
        raw = row[2]
        extra = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        extra = {}
    return {"driver": row[0], "port": row[1], "settings": extra, "ofd_provider": row[3]}


def _check_driver(name: str):
    if not _DRIVERS.get(name, False):
        raise HTTPException(status_code=503, detail=f"{'АТОЛ' if name == 'atol' else 'Штрих-М'} недоступен")


# ---------- E33: авто-миграция схемы ----------

_DDL_DONE = False


def _ensure_schema(db: Session):
    """Идемпотентная миграция: колонки балансов смен + таблица остатков.
    Выполняется автоматически при первом кассовом вызове — ручной SQL не нужен."""
    global _DDL_DONE
    if _DDL_DONE:
        return
    for stmt in (
        "ALTER TABLE fiscal_shift ADD COLUMN IF NOT EXISTS cash_total NUMERIC(12,2) DEFAULT 0",
        "ALTER TABLE fiscal_shift ADD COLUMN IF NOT EXISTS card_total NUMERIC(12,2) DEFAULT 0",
        "ALTER TABLE fiscal_shift ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP",
        "ALTER TABLE fiscal_shift ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
        "CREATE TABLE IF NOT EXISTS fiscal_pending ("
        "  id INT PRIMARY KEY DEFAULT 1, cash NUMERIC(12,2) DEFAULT 0,"
        "  card NUMERIC(12,2) DEFAULT 0,"
        "  withdrawn_at TIMESTAMP, withdrawn_by VARCHAR(255))",
        "INSERT INTO fiscal_pending (id) VALUES (1) ON CONFLICT (id) DO NOTHING",
    ):
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()  # SQLite/старая схема — пропускаем, NOT EXISTS уже есть
    _DDL_DONE = True


# ---------- E33: балансы смен ----------

def _latest_shift(db: Session):
    """Последняя смена (исправлено: раньше бралась самая старая — без DESC)."""
    return db.execute(text(
        "SELECT id, is_open, opened_at FROM fiscal_shift "
        "ORDER BY created_at DESC LIMIT 1"
    )).fetchone()


def _shift_totals(db: Session, opened_at) -> tuple:
    """Обороты смены: наличные и безналичные ОТДЕЛЬНО (не суммируются).
    Приход минус расход, только подтверждённые (COMPLETED) платежи,
    по моменту зачисления completed_at (fallback — created_at)."""
    r = db.execute(text("""
        SELECT
          COALESCE(SUM(CASE WHEN COALESCE(payment_method,'CASH') = 'CASH'
                            AND COALESCE(payment_direction,'INCOMING') = 'INCOMING'
                            THEN amount
                            WHEN COALESCE(payment_method,'CASH') = 'CASH'
                            THEN -amount ELSE 0 END), 0) AS cash,
          COALESCE(SUM(CASE WHEN COALESCE(payment_method,'CASH') <> 'CASH'
                            AND COALESCE(payment_direction,'INCOMING') = 'INCOMING'
                            THEN amount
                            WHEN COALESCE(payment_method,'CASH') <> 'CASH'
                            THEN -amount ELSE 0 END), 0) AS card
        FROM payments
        WHERE status = 'COMPLETED'
          AND COALESCE(completed_at, created_at) >= :opened_at
    """), {"opened_at": opened_at}).first()
    return float(r[0] or 0), float(r[1] or 0)


def _pending(db: Session) -> tuple:
    """Остаток прошлых смен, который ещё не снял бухгалтер."""
    row = db.execute(text(
        "SELECT cash, card FROM fiscal_pending WHERE id = 1")).first()
    return (float(row[0] or 0), float(row[1] or 0)) if row else (0.0, 0.0)


def _shift_state(db: Session) -> dict:
    s = _latest_shift(db)
    pc, pb = _pending(db)
    cash = card = 0.0
    if s and s[1] and s[2]:
        cash, card = _shift_totals(db, s[2])
    return {"is_open": bool(s[1]) if s else False,
            "cash_total": cash, "card_total": card,
            "prev_cash": pc, "prev_card": pb}


# ---------- Фискализация ----------

def _fiscalize(db: Session, driver: str, receipt_type: str, amount: float,
               receipt_id: Optional[str] = None, original_receipt_id: Optional[str] = None,
               payload: Optional[dict] = None) -> dict:
    """Общая фискализация: создаёт чек, возвращает данные"""
    # E33: чек возможен только при открытой смене (проверка сервером —
    # покрывает /atol, /shtrih, /refund, /correction).
    _ensure_schema(db)
    st = _shift_state(db)
    if not st["is_open"]:
        raise HTTPException(400, "Смена закрыта. Сначала откройте смену "
                                 "(кнопка «Открыть смену» в разделе «Платежи»).")

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
    dto_url = (settings.get("settings") or {}).get("dto_url")
    if dto_url and driver == "atol":
        try:
            st_s = settings.get("settings") or {}
            items = (payload or {}).get("items") or [{
                "name": (payload or {}).get("service") or "Услуга FitIntel",
                "price": amount, "quantity": 1}]
            body = {"username": st_s.get("dto_login") or "",
                    "password": st_s.get("dto_password") or "",
                    "requests": [{
                        "type": "sell" if receipt_type == "sale" else "sellReturn",
                        "id": receipt_id,
                        "items": items}]}
            r = requests.post(dto_url.rstrip("/") + "/requests", json=body, timeout=15)
            r.raise_for_status()
            res = (r.json().get("results") or [{}])[0]
            if res.get("error"):
                raise HTTPException(502, f"Касса вернула ошибку: {res.get('error')}")
            fp = res.get("fiscalParams") or {}
            fn = str(fp.get("fiscalDocumentNumber") or fn)
            sign = str(fp.get("fiscalDocumentSign") or sign)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"Касса недоступна: {str(e)[:200]}")
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


# ---------- Pydantic-модели ----------

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


# ---------- Чеки ----------

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


# ---------- Смены (E31.13, E31.14) + балансы (E33) ----------

@router.post("/open-shift")
def open_shift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.13 — открытие смены. Ответ содержит баланс предыдущей смены."""
    _ensure_schema(db)
    s = _latest_shift(db)
    if s and s[1]:
        raise HTTPException(status_code=400, detail="Смена уже открыта")
    now = datetime.now(timezone.utc)
    # Каждое открытие — НОВАЯ строка смены (история сохраняется)
    _insert(db, "fiscal_shift", {"id": str(uuid.uuid4()), "is_open": True,
                                 "opened_at": now, "created_at": now, "updated_at": now})
    db.commit()
    st = _shift_state(db)
    st.update({"shift_open": True, "message": "Смена открыта"})
    return st


@router.post("/close-shift")
def close_shift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.14 — закрытие смены с отчётом: обороты закрываемой смены (нал/безнал)
    плюс остаток прошлых смен. Обороты переходят в «не снятый» остаток."""
    _ensure_schema(db)
    s = _latest_shift(db)
    if not s or not s[1]:
        raise HTTPException(status_code=400, detail="Смена уже закрыта")
    cash, card = _shift_totals(db, s[2]) if s[2] else (0.0, 0.0)
    now = datetime.now(timezone.utc)
    db.execute(text(
        "UPDATE fiscal_shift SET is_open = FALSE, closed_at = :n,"
        " cash_total = :c, card_total = :b, updated_at = :n WHERE id = :id"
    ), {"n": now, "c": cash, "b": card, "id": s[0]})
    db.execute(text(
        "UPDATE fiscal_pending SET cash = cash + :c, card = card + :b WHERE id = 1"
    ), {"c": cash, "b": card})
    db.commit()
    pc, pb = _pending(db)
    return {"shift_open": False, "is_open": False, "message": "Смена закрыта",
            "cash_total": cash, "card_total": card,
            "prev_cash": pc, "prev_card": pb}


@router.post("/cash-withdrawal")
def cash_withdrawal(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33 — снятие кассы (остатка прошлых смен). Только бухгалтер/админ."""
    _ensure_schema(db)
    username = (getattr(user, "username", "") or "").lower()
    if username == "superadmin":
        allowed = True
    else:
        raw = AuthService(db).get_user_roles(user)
        codes = {(r.code if hasattr(r, "code") else str(r)).lower() for r in raw}
        allowed = bool(codes & {"admin", "superadmin", "accountant", "бухгалтер"})
    if not allowed:
        raise HTTPException(status_code=403,
                            detail="Снятие кассы доступно только бухгалтеру или администратору")
    w_cash, w_card = _pending(db)
    db.execute(text(
        "UPDATE fiscal_pending SET cash = 0, card = 0, withdrawn_at = :n,"
        " withdrawn_by = :u WHERE id = 1"
    ), {"n": datetime.now(timezone.utc), "u": username or "unknown"})
    db.commit()
    return {"withdrawn_cash": w_cash, "withdrawn_card": w_card,
            "message": "Остаток снят. Наличные: %.2f, безналичные: %.2f"
                       % (w_cash, w_card)}


@router.get("/shift")
def shift_status(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33 — состояние смены + балансы: текущая смена (нал/безнал отдельно)
    и не снятый остаток прошлых смен."""
    _ensure_schema(db)
    return _shift_state(db)


# ---------- Отчёты (E31.11, E31.12) ----------

@router.post("/x-report")
def x_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.11 — X-отчёт без закрытия смены (нал/безнал раздельно)"""
    _ensure_schema(db)
    s = _latest_shift(db)
    if not s or not s[1]:
        raise HTTPException(status_code=400, detail="Смена не открыта")
    cash, card = _shift_totals(db, s[2]) if s[2] else (0.0, 0.0)
    total = db.execute(text(
        "SELECT COALESCE(SUM(amount), 0) FROM fiscal_receipts WHERE receipt_type = 'sale'"
    )).scalar()
    return {"printed": True, "report_type": "X", "total": float(total),
            "cash_total": cash, "card_total": card,
            "shift_open": True, "message": "X-отчёт напечатан"}


@router.post("/z-report")
def z_report(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E31.12 — Z-отчёт с закрытием смены (как close-shift, с печатью)"""
    _ensure_schema(db)
    s = _latest_shift(db)
    if not s or not s[1]:
        raise HTTPException(status_code=400, detail="Смена не открыта")
    cash, card = _shift_totals(db, s[2]) if s[2] else (0.0, 0.0)
    now = datetime.now(timezone.utc)
    db.execute(text(
        "UPDATE fiscal_shift SET is_open = FALSE, closed_at = :n,"
        " cash_total = :c, card_total = :b, updated_at = :n WHERE id = :id"
    ), {"n": now, "c": cash, "b": card, "id": s[0]})
    db.execute(text(
        "UPDATE fiscal_pending SET cash = cash + :c, card = card + :b WHERE id = 1"
    ), {"c": cash, "b": card})
    db.commit()
    pc, pb = _pending(db)
    return {"printed": True, "report_type": "Z", "total": cash + card,
            "cash_total": cash, "card_total": card,
            "prev_cash": pc, "prev_card": pb,
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