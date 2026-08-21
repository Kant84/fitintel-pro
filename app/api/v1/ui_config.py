# app/api/v1/ui_config.py
"""E51 — UI-Config: настройка экранов тонкого клиента по ролям.

Суперадминистратор управляет матрицей «роль → экраны» (что видит
кассир/тренер/менеджер). Тонкий клиент при входе запрашивает
GET /ui-config/my и строит меню по видимым экранам.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles

get_db = None
for mod in ("app.db.session", "app.core.database", "app.database"):
    try:
        m = __import__(mod, fromlist=["get_db"])
        get_db = getattr(m, "get_db", None)
        if get_db is not None:
            break
    except Exception:
        continue

router = APIRouter(prefix="/ui-config", tags=["UI Config"])

ROLES = ["superadmin", "admin", "manager", "trainer", "reception"]

DEFAULT_PROFILES = {
    "superadmin": ["dashboard", "clients", "subscriptions", "visits", "schedule",
                   "payments", "reports", "analytics", "documents", "devices",
                   "users", "roles", "face_id", "license", "settings",
                   "ui_config", "setup"],
    "admin": ["dashboard", "clients", "subscriptions", "visits", "schedule",
              "payments", "reports", "analytics", "documents", "devices",
              "users", "roles", "face_id", "license", "settings"],
    "manager": ["dashboard", "clients", "subscriptions", "visits", "schedule",
                "payments", "reports", "documents"],
    "trainer": ["dashboard", "schedule", "visits", "clients"],
    "reception": ["dashboard", "clients", "visits", "subscriptions",
                  "payments", "face_id"],
}

PROTECTED_SUPERADMIN_SCREEN = "ui_config"

ROLE_ALIASES = {
    "administrator": "admin",
    "super_admin": "superadmin",
    "superuser": "superadmin",
    "root": "superadmin",
    "receptionist": "reception",
    "coach": "trainer",
}


def _user_role(user: Any) -> str:
    for attr in ("role", "role_name"):
        r = getattr(user, attr, None)
        if r is None:
            continue
        if hasattr(r, "value"):
            r = r.value
        if isinstance(r, str) and r:
            return ROLE_ALIASES.get(r.lower(), r.lower())
    roles = getattr(user, "roles", None)
    if roles:
        try:
            first = list(roles)[0]
            name = getattr(first, "name", None) or getattr(first, "code", None)
            if name is None and isinstance(first, str):
                name = first
            if name:
                return ROLE_ALIASES.get(str(name).lower(), str(name).lower())
        except Exception:
            pass
    return "admin"


def _all_screens(db: Session) -> list[dict]:
    rows = db.execute(text("""
        SELECT code, name, path, icon, sort_order, is_active
        FROM ui_screens ORDER BY sort_order, code
    """)).mappings().all()
    return [dict(r) for r in rows]


def _existing_codes(db: Session) -> set[str]:
    return {r[0] for r in db.execute(text("SELECT code FROM ui_screens")).all()}


def _replace_role_screens(db: Session, role: str, visible: set[str]) -> None:
    db.execute(text("DELETE FROM ui_role_screens WHERE role = :role"), {"role": role})
    for code in _existing_codes(db):
        db.execute(text("""
            INSERT INTO ui_role_screens (role, screen_code, is_visible)
            VALUES (:role, :code, :vis)
            ON CONFLICT (role, screen_code) DO UPDATE SET is_visible = :vis
        """), {"role": role, "code": code, "vis": code in visible})


class ScreenCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    path: str = ""
    icon: str = "circle"
    sort_order: int = 100


class RoleScreensUpdate(BaseModel):
    screens: list[str] = Field(..., description="Коды видимых экранов")


@router.get("/screens")
def list_screens(
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Реестр всех экранов тонкого клиента."""
    return {"screens": _all_screens(db)}


@router.post("/screens", status_code=201)
def create_screen(
    payload: ScreenCreate,
    db: Session = Depends(get_db),
    user: Any = Depends(require_roles("superadmin", "admin")),
) -> dict[str, Any]:
    """Зарегистрировать новый экран (superadmin/admin)."""
    code = payload.code.strip().lower()
    if code in _existing_codes(db):
        raise HTTPException(status_code=409, detail=f"Экран {code} уже существует")
    db.execute(text("""
        INSERT INTO ui_screens (code, name, path, icon, sort_order)
        VALUES (:code, :name, :path, :icon, :so)
    """), {"code": code, "name": payload.name, "path": payload.path,
           "icon": payload.icon, "so": payload.sort_order})
    db.execute(text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        VALUES ('superadmin', :code, TRUE)
        ON CONFLICT (role, screen_code) DO NOTHING
    """), {"code": code})
    db.commit()
    return {"code": code, "name": payload.name, "status": "created"}


@router.get("/roles")
def roles_matrix(
    db: Session = Depends(get_db),
    user: Any = Depends(require_roles("superadmin", "admin")),
) -> dict[str, Any]:
    """Полная матрица «роль → экраны»."""
    rows = db.execute(text("""
        SELECT role, screen_code, is_visible FROM ui_role_screens
    """)).mappings().all()
    matrix: dict[str, list[dict[str, Any]]] = {r: [] for r in ROLES}
    for row in rows:
        matrix.setdefault(row["role"], []).append(
            {"screen_code": row["screen_code"], "is_visible": row["is_visible"]})
    return {"roles": matrix}

@router.get("/roles/{role}/screens")
def role_screens(
    role: str,
    db: Session = Depends(get_db),
    user: Any = Depends(require_roles("superadmin", "admin")),
) -> dict[str, Any]:
    """Экраны конкретной роли с названиями."""
    role = role.lower()
    if role not in ROLES:
        raise HTTPException(status_code=404, detail=f"Неизвестная роль: {role}")
    rows = db.execute(text("""
        SELECT rs.screen_code, rs.is_visible, s.name, s.sort_order
        FROM ui_role_screens rs
        JOIN ui_screens s ON s.code = rs.screen_code
        WHERE rs.role = :role
        ORDER BY s.sort_order, rs.screen_code
    """), {"role": role}).mappings().all()
    return {"role": role, "screens": [dict(r) for r in rows]}


@router.put("/roles/{role}/screens")
def set_role_screens(
    role: str,
    payload: RoleScreensUpdate,
    db: Session = Depends(get_db),
    user: Any = Depends(require_roles("superadmin", "admin")),
) -> dict[str, Any]:
    """Задать видимые экраны роли (остальные скрываются)."""
    role = role.lower()
    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Неизвестная роль: {role}")
    codes = {c.strip().lower() for c in payload.screens}
    unknown = sorted(codes - _existing_codes(db))
    if unknown:
        raise HTTPException(status_code=400,
                            detail=f"Неизвестные экраны: {', '.join(unknown)}")
    if role == "superadmin" and PROTECTED_SUPERADMIN_SCREEN not in codes:
        raise HTTPException(
            status_code=400,
            detail="Нельзя скрыть экран настройки у суперадминистратора")
    _replace_role_screens(db, role, codes)
    db.commit()
    total = len(_existing_codes(db))
    return {"role": role, "visible": len(codes), "hidden": total - len(codes)}


@router.post("/roles/{role}/reset")
def reset_role(
    role: str,
    db: Session = Depends(get_db),
    user: Any = Depends(require_roles("superadmin", "admin")),
) -> dict[str, Any]:
    """Сбросить экраны роли к профилю по умолчанию."""
    role = role.lower()
    if role not in ROLES:
        raise HTTPException(status_code=404, detail=f"Неизвестная роль: {role}")
    defaults = set(DEFAULT_PROFILES[role])
    _replace_role_screens(db, role, defaults)
    db.commit()
    return {"role": role, "visible": len(defaults), "status": "reset"}


@router.get("/my")
def my_screens(
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Видимые экраны текущего пользователя — тонкий клиент строит меню."""
    role = _user_role(user)
    rows = db.execute(text("""
        SELECT s.code, s.name, s.path, s.icon, s.sort_order
        FROM ui_role_screens rs
        JOIN ui_screens s ON s.code = rs.screen_code
        WHERE rs.role = :role AND rs.is_visible AND s.is_active
        ORDER BY s.sort_order, s.code
    """), {"role": role}).mappings().all()
    screens = [dict(r) for r in rows]
    if not screens:
        defaults = set(DEFAULT_PROFILES.get(role, []))
        screens = [s for s in _all_screens(db)
                   if s["code"] in defaults and s["is_active"]]
        for s in screens:
            s.pop("is_active", None)
    return {"role": role, "screens": screens}
