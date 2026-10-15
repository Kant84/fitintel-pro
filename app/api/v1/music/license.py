#app\api\v1\music\license.py
# -*- coding: utf-8 -*-
"""Лицензионный блок коммерческого фонового воспроизведения.
Статусы: ok (действует) | warning (не указана — для зала нужна) | expired (истекла).
Проверка в play/energize: expired -> 402; warning -> разрешено (режим провайдера
несёт свою лицензию), но статус горит предупреждением. Не юридическая консультация:
публичное исполнение в РФ — РАО/ВОИС/НКП или договор с провайдером музыки."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_db
from . import deps

router = APIRouter()

DDL_LICENSE = [
    """
    CREATE TABLE IF NOT EXISTS music_license (
        id INTEGER PRIMARY KEY DEFAULT 1,
        license_type VARCHAR(20) NOT NULL DEFAULT 'none',  -- none | provider | rao_vois
        provider_name VARCHAR(100),
        contract_number VARCHAR(100),
        valid_until DATE,
        updated_at TIMESTAMP NOT NULL DEFAULT now()
    )
    """,
    "INSERT INTO music_license (id) VALUES (1) ON CONFLICT (id) DO NOTHING",
]


def _ensure_license(db):
    for stmt in DDL_LICENSE:
        db.execute(text(stmt))
    db.commit()


def license_status(db):
    """-> (status, data): status in ok | warning | expired"""
    _ensure_license(db)
    r = db.execute(text("SELECT * FROM music_license WHERE id=1")).first()
    d = deps.row(r) if r else {}
    lt = d.get("license_type") or "none"
    vu = d.get("valid_until")
    if lt == "none":
        return "warning", d
    if vu and vu < datetime.date.today():
        return "expired", d
    return "ok", d


def enforce(db):
    """Блокировка фонового воспроизведения: только при статусе ok.
    warning (не указана) и expired (истекла) -> 402."""
    st, d = license_status(db)
    if st == "expired":
        raise HTTPException(402, "Лицензия на фоновую музыку истекла (%s). "
                                 "Обновите договор: ⚙ Музыка/DJ → Лицензия." % d.get("valid_until"))
    if st == "warning":
        raise HTTPException(402, "Лицензия на фоновую музыку не указана — фоновое "
                                 "воспроизведение недоступно. Внесите договор "
                                 "(РАО/ВОИС или провайдер): ⚙ Музыка/DJ → Лицензия.")

class LicenseIn(BaseModel):
    license_type: str = "none"          # none | provider | rao_vois
    provider_name: str = ""
    contract_number: str = ""
    valid_until: str | None = None      # "2027-12-31"


@router.get("/license")
def license_get(db=Depends(get_db)):
    st, d = license_status(db)
    return {"status": st, **{k: (str(v) if v is not None else None) for k, v in d.items()
                             if k not in ("id", "updated_at")}}


@router.post("/license")
def license_set(body: LicenseIn, db=Depends(get_db)):
    _ensure_license(db)
    db.execute(text(
        "UPDATE music_license SET license_type=:t, provider_name=:p,"
        " contract_number=:c, valid_until=:v, updated_at=now() WHERE id=1"),
        {"t": body.license_type, "p": body.provider_name,
         "c": body.contract_number, "v": body.valid_until})
    db.commit()
    st, d = license_status(db)
    return {"ok": True, "status": st, "valid_until": str(d.get("valid_until"))}