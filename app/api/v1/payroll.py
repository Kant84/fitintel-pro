# app/api/v1/payroll.py
"""ЗП сотрудников: штатное расписание, индивидуальные параметры, ежемесячные начисления."""
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text as _text
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(tags=["Payroll"])


class PositionIn(BaseModel):
    code: str
    name: str
    base_salary: float = 0


class PositionPatch(BaseModel):
    name: Optional[str] = None
    base_salary: Optional[float] = None


class PayrollIn(BaseModel):
    position_id: Optional[str] = None
    base_salary: Optional[float] = None   # None -> брать из штатки
    rate_per_hour: Optional[float] = None
    commission_percent: Optional[float] = None


class MonthlyIn(BaseModel):
    period: str                           # YYYY-MM
    advance: float = 0                    # аванс
    deductions: float = 0                 # удержания
    fines: float = 0                      # штрафы
    bonus: float = 0                      # премия
    note: Optional[str] = None


_DDL = [
    """CREATE TABLE IF NOT EXISTS staff_positions (
        id UUID PRIMARY KEY, code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL, base_salary NUMERIC(12,2) NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS staff_payroll (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        position_id UUID REFERENCES staff_positions(id) ON DELETE SET NULL,
        base_salary NUMERIC(12,2),
        rate_per_hour NUMERIC(12,2) NOT NULL DEFAULT 0,
        commission_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS payroll_monthly (
        id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        period VARCHAR(7) NOT NULL, advance NUMERIC(12,2) NOT NULL DEFAULT 0,
        deductions NUMERIC(12,2) NOT NULL DEFAULT 0, fines NUMERIC(12,2) NOT NULL DEFAULT 0,
        bonus NUMERIC(12,2) NOT NULL DEFAULT 0, note VARCHAR(500),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        UNIQUE (user_id, period))""",
]


def _ensure(db: Session):
    for ddl in _DDL:
        db.execute(_text(ddl))
    db.execute(_text("ALTER TABLE payroll_monthly ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0"))
    db.execute(_text("ALTER TABLE payroll_monthly ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITH TIME ZONE"))
    db.commit()


def _row(r):
    d = dict(r)
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# ---------- штатное расписание ----------
@router.get("/staff/positions")
def list_positions(current_user=Depends(require_permission("users.read")),
                   db: Session = Depends(get_db)):
    _ensure(db)
    rows = db.execute(_text(
        "SELECT id, code, name, base_salary FROM staff_positions ORDER BY name")).mappings().all()
    return {"items": [_row(r) for r in rows]}


@router.post("/staff/positions")
def add_position(body: PositionIn,
                 current_user=Depends(require_permission("users.update")),
                 db: Session = Depends(get_db)):
    _ensure(db)
    code = (body.code or "").strip().lower()
    if not code:
        raise HTTPException(400, "code обязателен")
    if db.execute(_text("SELECT 1 FROM staff_positions WHERE code=:c"), {"c": code}).first():
        raise HTTPException(409, "Должность с таким кодом уже есть")
    pid = str(uuid4())
    db.execute(_text(
        "INSERT INTO staff_positions (id, code, name, base_salary) VALUES (:i,:c,:n,:s)"),
        {"i": pid, "c": code, "n": body.name.strip(), "s": body.base_salary or 0})
    db.commit()
    return {"id": pid}


@router.patch("/staff/positions/{position_id}")
def patch_position(position_id: UUID, body: PositionPatch,
                   current_user=Depends(require_permission("users.update")),
                   db: Session = Depends(get_db)):
    _ensure(db)
    fields, params = [], {"i": str(position_id)}
    if body.name is not None:
        fields.append("name=:n"); params["n"] = body.name.strip()
    if body.base_salary is not None:
        fields.append("base_salary=:s"); params["s"] = body.base_salary
    if fields:
        db.execute(_text("UPDATE staff_positions SET " + ", ".join(fields) + " WHERE id=:i"), params)
        db.commit()
    return {"ok": True}


@router.delete("/staff/positions/{position_id}")
def del_position(position_id: UUID,
                 current_user=Depends(require_permission("users.update")),
                 db: Session = Depends(get_db)):
    _ensure(db)
    db.execute(_text("DELETE FROM staff_positions WHERE id=:i"), {"i": str(position_id)})
    db.commit()
    return {"ok": True}


# ---------- индивидуальные параметры ----------
@router.get("/staff/payroll/{user_id}")
def get_payroll(user_id: UUID,
                current_user=Depends(require_permission("users.read")),
                db: Session = Depends(get_db)):
    _ensure(db)
    r = db.execute(_text(
        """SELECT sp.user_id, sp.position_id, sp.base_salary, sp.rate_per_hour,
                  sp.commission_percent, p.name AS position_name, p.base_salary AS position_salary
           FROM staff_payroll sp LEFT JOIN staff_positions p ON p.id = sp.position_id
           WHERE sp.user_id = :u"""), {"u": str(user_id)}).mappings().first()
    if not r:
        return {"user_id": str(user_id), "position_id": None, "base_salary": None,
                "rate_per_hour": 0, "commission_percent": 0, "position_name": None, "position_salary": None}
    return _row(r)


@router.patch("/staff/payroll/{user_id}")
def set_payroll(user_id: UUID, body: PayrollIn,
                current_user=Depends(require_permission("users.update")),
                db: Session = Depends(get_db)):
    _ensure(db)
    db.execute(_text(
        """INSERT INTO staff_payroll (user_id, position_id, base_salary, rate_per_hour, commission_percent)
           VALUES (:u, :p, :b, :r, :c)
           ON CONFLICT (user_id) DO UPDATE SET
             position_id = COALESCE(EXCLUDED.position_id, staff_payroll.position_id),
             base_salary = COALESCE(EXCLUDED.base_salary, staff_payroll.base_salary),
             rate_per_hour = COALESCE(EXCLUDED.rate_per_hour, staff_payroll.rate_per_hour),
             commission_percent = COALESCE(EXCLUDED.commission_percent, staff_payroll.commission_percent),
             updated_at = now()"""),
        {"u": str(user_id), "p": body.position_id, "b": body.base_salary,
         "r": body.rate_per_hour, "c": body.commission_percent})
    db.commit()
    return {"ok": True}


# ---------- ежемесячные начисления ----------
@router.get("/payroll/monthly")
def get_monthly(user_id: UUID, period: str,
                current_user=Depends(require_permission("users.read")),
                db: Session = Depends(get_db)):
    _ensure(db)
    r = db.execute(_text(
        "SELECT * FROM payroll_monthly WHERE user_id=:u AND period=:p"),
        {"u": str(user_id), "p": period}).mappings().first()
    return _row(r) if r else {"user_id": str(user_id), "period": period,
                              "advance": 0, "deductions": 0, "fines": 0, "bonus": 0, "note": None}


@router.post("/payroll/monthly")
def set_monthly(body: MonthlyIn, user_id: UUID,
                current_user=Depends(require_permission("users.update")),
                db: Session = Depends(get_db)):
    _ensure(db)
    db.execute(_text(
        """INSERT INTO payroll_monthly (id, user_id, period, advance, deductions, fines, bonus, note)
           VALUES (:i, :u, :p, :a, :d, :f, :b, :n)
           ON CONFLICT (user_id, period) DO UPDATE SET
             advance=:a, deductions=:d, fines=:f, bonus=:b, note=:n"""),
        {"i": str(uuid4()), "u": str(user_id), "p": body.period, "a": body.advance,
         "d": body.deductions, "f": body.fines, "b": body.bonus, "n": body.note})
    db.commit()
    return {"ok": True}


# ---------- расчёт за месяц ----------
@router.get("/payroll/calc")
def calc(period: str = Query(..., pattern="^\d{4}-\d{2}$"),
         current_user=Depends(require_permission("users.read")),
         db: Session = Depends(get_db)):
    _ensure(db)
    y, m = period.split("-")
    from calendar import monthrange
    d_from, d_to = "%s-%s-01" % (y, m), "%s-%s-%02d" % (y, m, monthrange(int(y), int(m))[1])
    users = db.execute(_text(
        "SELECT id, COALESCE(NULLIF(full_name,''), username) AS name FROM users WHERE is_active")).mappings().all()
    items = []
    for u in users:
        uid = str(u["id"])
        pr = db.execute(_text(
            """SELECT sp.base_salary, sp.commission_percent, p.base_salary AS pos_salary, p.name AS pos_name
               FROM staff_payroll sp LEFT JOIN staff_positions p ON p.id = sp.position_id
               WHERE sp.user_id=:u"""), {"u": uid}).mappings().first()
        base = None
        pos_name = None
        commission_p = 0.0
        if pr:
            base = float(pr["base_salary"]) if pr["base_salary"] is not None else (
                float(pr["pos_salary"]) if pr["pos_salary"] is not None else 0.0)
            pos_name = pr["pos_name"]
            commission_p = float(pr["commission_percent"] or 0)
        base = base or 0.0
        earnings = 0.0
        try:
            r = db.execute(_text(
                """SELECT COALESCE(SUM(ts.amount),0) AS s FROM trainer_sales ts
                   JOIN trainer_profiles tp ON tp.id = ts.trainer_id
                   WHERE tp.user_id = :u AND ts.created_at::date BETWEEN :f AND :t"""),
                {"u": uid, "f": d_from, "t": d_to}).first()
            earnings = float(r[0]) if r else 0.0
        except Exception:
            earnings = 0.0
        commission = round(earnings * commission_p / 100.0, 2)
        acc = db.execute(_text(
            "SELECT advance, deductions, fines, bonus FROM payroll_monthly WHERE user_id=:u AND period=:p"),
            {"u": uid, "p": period}).mappings().first()
        advance = float(acc["advance"]) if acc else 0.0
        deductions = float(acc["deductions"]) if acc else 0.0
        fines = float(acc["fines"]) if acc else 0.0
        bonus = float(acc["bonus"]) if acc else 0.0
        total = round(base + earnings + commission + bonus - advance - deductions - fines, 2)
        items.append({"user_id": uid, "name": u["name"], "position": pos_name or "—",
                      "base_salary": base, "earnings": earnings, "commission_percent": commission_p,
                      "commission": commission, "bonus": bonus, "advance": advance,
                      "deductions": deductions, "fines": fines, "total": total})
    return {"period": period, "items": items, "count": len(items)}

# ---------- выплата ЗП ----------
class PayIn(BaseModel):
    period: str
    amount: float


@router.post("/payroll/monthly/pay")
def payroll_monthly_pay(user_id: UUID, body: PayIn,
                        current_user=Depends(require_permission("users.update")),
                        db: Session = Depends(get_db)):
    _ensure(db)
    db.execute(_text(
        """INSERT INTO payroll_monthly (id, user_id, period, paid_amount, paid_at)
           VALUES (:i, :u, :p, :a, now())
           ON CONFLICT (user_id, period) DO UPDATE SET paid_amount=:a, paid_at=now()"""),
        {"i": str(uuid4()), "u": str(user_id), "p": body.period, "a": body.amount})
    # проводки: начисление Дт 44 Кт 70, выплата Дт 70 Кт 50
    try:
        from datetime import date as _d
        nm = db.execute(_text(
            "SELECT COALESCE(NULLIF(full_name,''), username) FROM users WHERE id=:u"),
            {"u": str(user_id)}).first()
        name = nm[0] if nm else str(user_id)[:8]
        dt = _d.today().isoformat()
        for doc_type, dr, cr, desc in (
                ("PAYROLL_ACCRUE", "44", "70", "ЗП начислена: %s (%s)" % (name, body.period)),
                ("PAYROLL_PAY", "70", "50", "ЗП выплачена: %s (%s)" % (name, body.period))):
            db.execute(_text(
                """INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description)
                   VALUES (:i, :dt, :t, :n, :d, :c, :a, :s)"""),
                {"i": str(uuid4()), "dt": dt, "t": doc_type, "n": "PAY-%s" % body.period,
                 "d": dr, "c": cr, "a": body.amount, "s": desc})
    except Exception:
        pass
    db.commit()
    return {"ok": True, "entries": True}
