"""E38: Корпоративные продажи (ТЗ v3.2 §4.12).

Компании (ИНН, скидка), корпоративные договоры с лимитом мест,
сотрудники по договору, счета компании, отчёт по компании.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/corporate", tags=["corporate"])

_FMT = "%Y-%m-%d %H:%M:%S"


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


def _client_exists(db, client_id):
    try:
        cid = uuid.UUID(str(client_id))
    except (ValueError, AttributeError):
        return False
    row = db.execute(text("SELECT id FROM clients WHERE id=:i"), {"i": cid}).fetchone()
    return row is not None


def _get_company(db, company_id):
    row = db.execute(
        text("SELECT * FROM corporate_companies WHERE id=:i"), {"i": company_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return dict(row)


def _get_contract(db, contract_id):
    row = db.execute(
        text("SELECT * FROM corporate_contracts WHERE id=:i"), {"i": contract_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return dict(row)


class CompanyCreate(BaseModel):
    name: str
    inn: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    discount_percent: float = 0


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    discount_percent: Optional[float] = None
    status: Optional[str] = None


class ContractCreate(BaseModel):
    company_id: str
    tariff_id: Optional[str] = None
    seats: int = 1
    price: float = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class MemberAdd(BaseModel):
    client_id: str


class InvoiceCreate(BaseModel):
    amount: Optional[float] = None
    period: Optional[str] = None


@router.post("/companies", status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    if not payload.inn.isdigit() or len(payload.inn) not in (10, 12):
        raise HTTPException(status_code=400, detail="Некорректный ИНН")
    if payload.discount_percent < 0 or payload.discount_percent > 100:
        raise HTTPException(status_code=400, detail="Некорректная скидка")
    dup = db.execute(
        text("SELECT id FROM corporate_companies WHERE inn=:i"), {"i": payload.inn}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Компания с таким ИНН уже существует")
    cid = str(uuid.uuid4())
    _insert(db, "corporate_companies", {
        "id": cid, "name": payload.name, "inn": payload.inn,
        "contact_name": payload.contact_name, "contact_email": payload.contact_email,
        "contact_phone": payload.contact_phone, "discount_percent": payload.discount_percent,
        "status": "active", "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"company_id": cid, "name": payload.name, "status": "active", "message": "Компания зарегистрирована"}


@router.get("/companies")
def list_companies(status: Optional[str] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM corporate_companies WHERE 1=1"
    params = {}
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/companies/{company_id}")
def get_company(company_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_company(db, company_id)


@router.put("/companies/{company_id}")
def update_company(company_id: str, payload: CompanyUpdate,
                   db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_company(db, company_id)
    if payload.discount_percent is not None and (payload.discount_percent < 0 or payload.discount_percent > 100):
        raise HTTPException(status_code=400, detail="Некорректная скидка")
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if fields:
        sets = ", ".join(f"{k}=:{k}" for k in fields)
        fields["cid"] = company_id
        db.execute(text(f"UPDATE corporate_companies SET {sets} WHERE id=:cid"), fields)
        db.commit()
    return {"message": "Компания обновлена"}


@router.get("/companies/{company_id}/report")
def company_report(company_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    comp = _get_company(db, company_id)
    contracts = db.execute(
        text("SELECT COUNT(*) FROM corporate_contracts WHERE company_id=:c"), {"c": company_id}
    ).scalar()
    members = db.execute(
        text("SELECT COUNT(*) FROM corporate_members m JOIN corporate_contracts ct ON m.contract_id=ct.id WHERE ct.company_id=:c AND m.status='active'"),
        {"c": company_id},
    ).scalar()
    invoiced = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM corporate_invoices WHERE company_id=:c"), {"c": company_id}
    ).scalar()
    paid = db.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM corporate_invoices WHERE company_id=:c AND status='paid'"), {"c": company_id}
    ).scalar()
    return {"company": comp["name"], "inn": comp["inn"], "contracts": contracts,
            "active_members": members, "invoiced_total": float(invoiced or 0), "paid_total": float(paid or 0)}


@router.post("/contracts", status_code=201)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    _get_company(db, payload.company_id)
    if payload.seats < 1:
        raise HTTPException(status_code=400, detail="Число мест должно быть не менее 1")
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="Цена не может быть отрицательной")
    cid = str(uuid.uuid4())
    number = "DOG-" + uuid.uuid4().hex[:8].upper()
    _insert(db, "corporate_contracts", {
        "id": cid, "company_id": payload.company_id, "number": number,
        "tariff_id": payload.tariff_id, "seats": payload.seats, "price": payload.price,
        "start_date": payload.start_date, "end_date": payload.end_date,
        "status": "draft", "created_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"contract_id": cid, "number": number, "status": "draft", "message": "Договор создан"}


@router.get("/contracts")
def list_contracts(company_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = "SELECT * FROM corporate_contracts WHERE 1=1"
    params = {}
    if company_id:
        q += " AND company_id=:c"
        params["c"] = company_id
    if status:
        q += " AND status=:s"
        params["s"] = status
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_contract(db, contract_id)


@router.post("/contracts/{contract_id}/activate")
def activate_contract(contract_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    ct = _get_contract(db, contract_id)
    if ct["status"] == "active":
        raise HTTPException(status_code=400, detail="Договор уже активирован")
    if ct["status"] == "terminated":
        raise HTTPException(status_code=400, detail="Договор расторгнут")
    db.execute(text("UPDATE corporate_contracts SET status='active' WHERE id=:i"), {"i": contract_id})
    db.commit()
    return {"message": "Договор активирован", "status": "active"}


@router.post("/contracts/{contract_id}/terminate")
def terminate_contract(contract_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    ct = _get_contract(db, contract_id)
    if ct["status"] != "active":
        raise HTTPException(status_code=400, detail="Договор не активен")
    db.execute(text("UPDATE corporate_contracts SET status='terminated' WHERE id=:i"), {"i": contract_id})
    db.execute(text("UPDATE corporate_members SET status='removed' WHERE contract_id=:i"), {"i": contract_id})
    db.commit()
    return {"message": "Договор расторгнут", "status": "terminated"}


@router.post("/contracts/{contract_id}/members", status_code=201)
def add_member(contract_id: str, payload: MemberAdd, db: Session = Depends(get_db),
               user=Depends(require_roles("admin"))):
    ct = _get_contract(db, contract_id)
    if ct["status"] != "active":
        raise HTTPException(status_code=400, detail="Договор не активен")
    dup = db.execute(
        text("SELECT id FROM corporate_members WHERE contract_id=:c AND client_id=:cl AND status='active'"),
        {"c": contract_id, "cl": payload.client_id},
    ).fetchone()
    if dup:
        raise HTTPException(status_code=409, detail="Сотрудник уже добавлен")
    count = db.execute(
        text("SELECT COUNT(*) FROM corporate_members WHERE contract_id=:c AND status='active'"),
        {"c": contract_id},
    ).scalar()
    if count >= (ct["seats"] or 1):
        raise HTTPException(status_code=409, detail="Лимит мест исчерпан")
    if not _client_exists(db, payload.client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    mid = str(uuid.uuid4())
    _insert(db, "corporate_members", {
        "id": mid, "contract_id": contract_id, "client_id": payload.client_id,
        "status": "active", "added_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"member_id": mid, "status": "active", "message": "Сотрудник добавлен"}


@router.get("/contracts/{contract_id}/members")
def list_members(contract_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _get_contract(db, contract_id)
    rows = db.execute(
        text("SELECT * FROM corporate_members WHERE contract_id=:c ORDER BY added_at DESC"),
        {"c": contract_id},
    ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.delete("/contracts/{contract_id}/members/{client_id}", status_code=204)
def remove_member(contract_id: str, client_id: str, db: Session = Depends(get_db),
                  user=Depends(require_roles("admin"))):
    _get_contract(db, contract_id)
    row = db.execute(
        text("SELECT id FROM corporate_members WHERE contract_id=:c AND client_id=:cl AND status='active'"),
        {"c": contract_id, "cl": client_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    db.execute(
        text("UPDATE corporate_members SET status='removed' WHERE contract_id=:c AND client_id=:cl"),
        {"c": contract_id, "cl": client_id},
    )
    db.commit()
    return None


@router.post("/contracts/{contract_id}/invoice", status_code=201)
def create_invoice(contract_id: str, payload: InvoiceCreate, db: Session = Depends(get_db),
                   user=Depends(require_roles("admin"))):
    ct = _get_contract(db, contract_id)
    if ct["status"] != "active":
        raise HTTPException(status_code=400, detail="Договор не активен")
    amount = payload.amount if payload.amount is not None else float(ct["price"] or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    iid = str(uuid.uuid4())
    period = payload.period or datetime.now().strftime("%Y-%m")
    _insert(db, "corporate_invoices", {
        "id": iid, "contract_id": contract_id, "company_id": ct["company_id"],
        "amount": amount, "period": period, "status": "issued",
        "issued_at": _fmt(datetime.now()),
    })
    db.commit()
    return {"invoice_id": iid, "amount": amount, "period": period, "status": "issued", "message": "Счёт выставлен"}


@router.post("/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    row = db.execute(
        text("SELECT * FROM corporate_invoices WHERE id=:i"), {"i": invoice_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    if row["status"] != "issued":
        raise HTTPException(status_code=400, detail="Счёт уже оплачен")
    db.execute(
        text("UPDATE corporate_invoices SET status='paid', paid_at=:p WHERE id=:i"),
        {"p": _fmt(datetime.now()), "i": invoice_id},
    )
    db.commit()
    return {"message": "Счёт оплачен", "status": "paid", "amount": row["amount"]}
