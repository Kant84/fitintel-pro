"""E48: Регламентированная отчётность (ТЗ v3.2 §16.2).

6-НДФЛ и РСВ: расчёт по начислениям сотрудников, XML-экспорт
(упрощённый), декларация УСН на данных учёта E32, календарь сдачи.
"""
import uuid
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:  # pragma: no cover
    try:
        from app.core.database import get_db
    except ImportError:
        from app.database import get_db

from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/reporting", tags=["reporting"])

_FMT = "%Y-%m-%d %H:%M:%S"
_NDFL_RATE = 0.13
_RSV_RATES = {"ops": 0.22, "oms": 0.051, "vnim": 0.029}  # суммарно 30%
_QUARTER_MONTHS = {1: ("01", "02", "03"), 2: ("04", "05", "06"),
                   3: ("07", "08", "09"), 4: ("10", "11", "12")}


def _fmt(dt):
    return dt.strftime(_FMT)


def _cols(db, table):
    rows = db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _insert(db, table, data):
    cols = _cols(db, table)
    d = {k: v for k, v in data.items() if k in cols}
    names = ", ".join(d.keys())
    params = ", ".join(":" + k for k in d.keys())
    db.execute(text(f"INSERT INTO {table} ({names}) VALUES ({params})"), d)


def _check_quarter(quarter):
    if quarter not in _QUARTER_MONTHS:
        raise HTTPException(status_code=400, detail="Некорректный квартал")


def _periods(year, quarter):
    return [f"{year}-{m}" for m in _QUARTER_MONTHS[quarter]]


def _payroll_for(db, periods):
    marks = ",".join(f"'{p}'" for p in periods)
    rows = db.execute(
        text(f"SELECT employee_name, inn, period, income, deductions FROM payroll_records WHERE period IN ({marks})")
    ).mappings().fetchall()
    return [dict(r) for r in rows]


def _ndfl_calc(rows):
    by_emp = {}
    for r in rows:
        key = (r["employee_name"], r.get("inn") or "")
        e = by_emp.setdefault(key, {"employee_name": key[0], "inn": key[1],
                                    "income": 0.0, "deductions": 0.0})
        e["income"] += float(r["income"] or 0)
        e["deductions"] += float(r["deductions"] or 0)
    employees = []
    for e in by_emp.values():
        base = max(e["income"] - e["deductions"], 0)
        ndfl = round(base * _NDFL_RATE, 2)
        employees.append({**e, "tax_base": round(base, 2), "ndfl": ndfl})
    return employees


class PayrollCreate(BaseModel):
    employee_name: str
    inn: Optional[str] = None
    period: str
    income: float
    deductions: float = 0


@router.post("/payroll/records", status_code=201)
def add_payroll(payload: PayrollCreate, db: Session = Depends(get_db),
                user=Depends(require_roles("admin"))):
    if payload.income < 0 or payload.deductions < 0:
        raise HTTPException(status_code=400, detail="Суммы не могут быть отрицательными")
    if len(payload.period) != 7 or payload.period[4] != "-":
        raise HTTPException(status_code=400, detail="Период должен быть YYYY-MM")
    rid = str(uuid.uuid4())
    _insert(db, "payroll_records", {
        "id": rid, "employee_name": payload.employee_name, "inn": payload.inn,
        "period": payload.period, "income": payload.income,
        "deductions": payload.deductions, "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"record_id": rid, "message": "Начисление добавлено"}


@router.get("/payroll/records")
def list_payroll(period: Optional[str] = Query(None), db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    q = "SELECT * FROM payroll_records WHERE 1=1"
    params = {}
    if period:
        q += " AND period=:p"
        params["p"] = period
    q += " ORDER BY period, employee_name"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.delete("/payroll/records/{record_id}", status_code=204)
def delete_payroll(record_id: str, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    row = db.execute(text("SELECT id FROM payroll_records WHERE id=:i"), {"i": record_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.execute(text("DELETE FROM payroll_records WHERE id=:i"), {"i": record_id})
    db.commit()
    return None


@router.get("/6ndfl")
def ndfl6(year: int = Query(...), quarter: int = Query(...),
          db: Session = Depends(get_db), user=Depends(get_current_user)):
    _check_quarter(quarter)
    rows = _payroll_for(db, _periods(year, quarter))
    employees = _ndfl_calc(rows)
    return {"report": "6-НДФЛ", "year": year, "quarter": quarter,
            "employees": employees,
            "totals": {
                "income": round(sum(e["income"] for e in employees), 2),
                "deductions": round(sum(e["deductions"] for e in employees), 2),
                "tax_base": round(sum(e["tax_base"] for e in employees), 2),
                "ndfl": round(sum(e["ndfl"] for e in employees), 2),
            }}


@router.get("/6ndfl/export")
def ndfl6_export(year: int = Query(...), quarter: int = Query(...),
                 db: Session = Depends(get_db), user=Depends(get_current_user)):
    _check_quarter(quarter)
    data = ndfl6(year, quarter, db, user)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<report type="6-NDFL" year="{year}" quarter="{quarter}">']
    for e in data["employees"]:
        lines.append(
            f'  <employee name="{escape(e["employee_name"])}" inn="{e["inn"]}" '
            f'income="{e["income"]}" base="{e["tax_base"]}" ndfl="{e["ndfl"]}"/>'
        )
    t = data["totals"]
    lines.append(f'  <totals income="{t["income"]}" base="{t["tax_base"]}" ndfl="{t["ndfl"]}"/>')
    lines.append("</report>")
    return PlainTextResponse("\n".join(lines), media_type="application/xml")


@router.get("/rsv")
def rsv(year: int = Query(...), quarter: int = Query(...),
        db: Session = Depends(get_db), user=Depends(get_current_user)):
    _check_quarter(quarter)
    rows = _payroll_for(db, _periods(year, quarter))
    by_emp = {}
    for r in rows:
        key = (r["employee_name"], r.get("inn") or "")
        by_emp[key] = by_emp.get(key, 0.0) + float(r["income"] or 0)
    employees = []
    for (name, inn), base in by_emp.items():
        employees.append({
            "employee_name": name, "inn": inn, "base": round(base, 2),
            "ops": round(base * _RSV_RATES["ops"], 2),
            "oms": round(base * _RSV_RATES["oms"], 2),
            "vnim": round(base * _RSV_RATES["vnim"], 2),
            "total": round(base * sum(_RSV_RATES.values()), 2),
        })
    return {"report": "РСВ", "year": year, "quarter": quarter, "employees": employees,
            "totals": {"base": round(sum(e["base"] for e in employees), 2),
                       "contributions": round(sum(e["total"] for e in employees), 2)}}


@router.get("/rsv/export")
def rsv_export(year: int = Query(...), quarter: int = Query(...),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    _check_quarter(quarter)
    data = rsv(year, quarter, db, user)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<report type="RSV" year="{year}" quarter="{quarter}">']
    for e in data["employees"]:
        lines.append(
            f'  <employee name="{escape(e["employee_name"])}" inn="{e["inn"]}" '
            f'base="{e["base"]}" ops="{e["ops"]}" oms="{e["oms"]}" vnimo="{e["vnim"]}"/>'
        )
    t = data["totals"]
    lines.append(f'  <totals base="{t["base"]}" contributions="{t["contributions"]}"/>')
    lines.append("</report>")
    return PlainTextResponse("\n".join(lines), media_type="application/xml")


@router.get("/usn-declaration")
def usn(year: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    income = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM accounting_entries WHERE credit_account='revenue'")
    ).scalar()
    expense = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM accounting_entries WHERE debit_account='expense'")
    ).scalar()
    income, expense = float(income or 0), float(expense or 0)
    tax_income = round(income * 0.06, 2)
    tax_diff = round((income - expense) * 0.15, 2)
    return {"report": "УСН", "year": year, "income": income, "expense": expense,
            "tax_income_6": tax_income, "tax_income_minus_expense_15": tax_diff,
            "recommended": "6%" if tax_income <= max(tax_diff, 0) else "15%"}


@router.get("/calendar")
def reporting_calendar(year: int = Query(2026), user=Depends(get_current_user)):
    return {"year": year, "deadlines": [
        {"report": "6-НДФЛ", "period": "Q1", "deadline": f"{year}-04-25"},
        {"report": "6-НДФЛ", "period": "Q2", "deadline": f"{year}-07-25"},
        {"report": "6-НДФЛ", "period": "Q3", "deadline": f"{year}-10-25"},
        {"report": "6-НДФЛ", "period": "Q4", "deadline": f"{year + 1}-02-25"},
        {"report": "РСВ", "period": "Q1", "deadline": f"{year}-04-25"},
        {"report": "РСВ", "period": "Q2", "deadline": f"{year}-07-25"},
        {"report": "РСВ", "period": "Q3", "deadline": f"{year}-10-25"},
        {"report": "РСВ", "period": "Q4", "deadline": f"{year + 1}-01-25"},
        {"report": "УСН", "period": "year", "deadline": f"{year + 1}-04-25"},
    ]}


@router.get("/summary")
def summary(year: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    periods = [f"{year}-{m:02d}" for m in range(1, 13)]
    marks = ",".join(f"'{p}'" for p in periods)
    n = db.execute(
        text(f"SELECT COUNT(*) FROM payroll_records WHERE period IN ({marks})")
    ).scalar()
    return {"year": year, "payroll_records": n,
            "reports": ["6-НДФЛ", "РСВ", "УСН"],
            "status": "ready" if n else "no_data"}
