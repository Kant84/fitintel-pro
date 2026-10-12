# W5: конфиг мини-приложения: brand (branding_settings/White-label) + настройки приложения + QR + отзывы
import urllib.parse as _up
import uuid as _uuid
from datetime import datetime as _dt, timezone as _tz

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import text as _t

from app.api.v1.club_params import get_param
from app.db.session import engine as _e

router = APIRouter()


def _brand() -> dict:
    try:
        with _e.connect() as c:
            row = c.execute(_t("SELECT * FROM branding_settings WHERE id=1")).mappings().first()
        return dict(row) if row else {}
    except Exception:
        return {}


def _app_cfg() -> dict:
    try:
        with _e.connect() as c:
            row = c.execute(_t("SELECT about, hours, support_phone, support_email, info_email, feedback_email, payments_enabled FROM max_bot_settings WHERE id=1")).first()
    except Exception:
        row = None
    g = lambda i, d="": (row[i] if row and row[i] else d)
    return {"about": g(0), "hours": g(1), "support_phone": g(2), "support_email": g(3),
            "info_email": g(4), "feedback_email": g(5),
            "payments_enabled": (bool(row[6]) if row and row[6] is not None else True)}


@router.get("/miniapp/config")
def miniapp_config() -> dict:
    b = _brand()
    a = _app_cfg()
    return {
        "club_name": b.get("club_name") or get_param("WL.CLUB_NAME", None) or get_param("CLUB_NAME", "Клуб"),
        "slogan": b.get("tagline") or "",
        "logo_url": b.get("logo_url") or "",
        "accent": b.get("accent_color") or "#00f0ff",
        "about": a["about"],
        "hours": a["hours"] or "Будни 8:30-23:00",
        "support_phone": a["support_phone"] or b.get("support_phone") or "",
        "support_email": a["support_email"] or b.get("support_email") or "",
        "info_email": a["info_email"] or "",
        "feedback_email": a["feedback_email"] or a["support_email"] or b.get("support_email") or "",
        "payments_enabled": a["payments_enabled"],
    }


@router.get("/miniapp/qr")
def miniapp_qr(data: str = Query(default="fitintel", max_length=512)):
    try:
        import io as _io
        import qrcode
        img = qrcode.make(data)
        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        return Response(buf.getvalue(), media_type="image/png")
    except Exception:
        return RedirectResponse("https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=" + _up.quote(data))


def _ensure_feedback():
    try:
        with _e.begin() as c:
            c.execute(_t("CREATE TABLE IF NOT EXISTS app_feedback (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), client_id TEXT, theme TEXT, body TEXT, created_at TIMESTAMP DEFAULT now())"))
    except Exception:
        pass


_ensure_feedback()


@router.post("/miniapp/feedback")
def miniapp_feedback(body: dict):
    _ensure_feedback()
    theme = str(body.get("theme") or "")[:200]
    body_ = str(body.get("body") or "")[:4000]
    if not body_.strip():
        return {"ok": False, "error": "Пустой отзыв"}
    with _e.begin() as c:
        c.execute(_t("INSERT INTO app_feedback (id, client_id, theme, body, created_at) VALUES (:i,:c,:t,:b,:n)"),
                  {"i": str(_uuid.uuid4()), "c": str(body.get("client_id") or ""), "t": theme, "b": body_, "n": _dt.now(_tz.utc)})
    return {"ok": True}


@router.get("/miniapp/feedback")
def miniapp_feedback_list(limit: int = Query(default=200, le=500)):
    _ensure_feedback()
    with _e.connect() as c:
        rows = c.execute(_t("SELECT id, client_id, theme, body, created_at FROM app_feedback ORDER BY created_at DESC LIMIT :l"), {"l": int(limit)}).fetchall()
    return {"items": [{"id": str(r[0]), "client_id": r[1], "theme": r[2], "body": r[3], "created_at": str(r[4])} for r in rows]}


# === W5: регистрация клиента в приложении (код из MAX/email) ===
import re as _re
from datetime import datetime as _dtn, timezone as _tzn

from fastapi import Depends as _Dep, HTTPException as _HE
from pydantic import BaseModel as _BM, Field as _FL
from sqlalchemy.orm import Session as _S

from app.db.session import get_db as _gdb


class RegisterIn(_BM):
    full_name: str = _FL(min_length=3, max_length=200)
    birth_year: int | None = None
    phone: str = _FL(min_length=10, max_length=24)
    email: str | None = None
    code: str = _FL(min_length=4, max_length=8)
    password: str = _FL(min_length=8, max_length=128)


@router.post("/miniapp/register")
def miniapp_register(body: RegisterIn, db: _S = _Dep(_gdb)):
    norm = _re.sub(r"\D", "", body.phone or "")[-10:]
    if len(norm) < 10:
        raise _HE(422, "Невалидный номер телефона")
    row = db.execute(_t("SELECT id, code, verified, expires_at, created_at FROM phone_verifications "
                        "WHERE right(regexp_replace(phone,'\D','','g'),10)=:p "
                        "ORDER BY created_at DESC LIMIT 1"), {"p": norm}).first()
    if not row:
        raise _HE(400, "Сначала нажмите «Получить код»")
    now = _dtn.now(_tzn.utc)
    if row[3] and now > row[3]:
        raise _HE(400, "Код истёк — запросите новый")
    if (now - row[4]).total_seconds() > 600:
        raise _HE(400, "Код устарел — запросите новый")
    if not row[2]:
        if (body.code or "") != (row[1] or ""):
            raise _HE(400, "Неверный код")
        db.execute(_t("UPDATE phone_verifications SET verified=true WHERE id=:i"), {"i": str(row[0])})
    with _e.begin() as c:
        c.execute(_t("ALTER TABLE clients ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)"))
        c.execute(_t("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE"))
    q = "SELECT 1 FROM users WHERE username=:u OR phone=:p"
    args = {"u": norm, "p": body.phone}
    if body.email:
        q += " OR email=:e"
        args["e"] = body.email
    if db.execute(_t(q + " LIMIT 1"), args).first():
        raise _HE(409, "Аккаунт с таким телефоном/email уже существует — войдите")
    from app.services.auth_service import AuthService
    svc = AuthService(db)
    user = svc.create_user(norm, body.password, body.email)
    db.execute(_t("UPDATE users SET phone=:p, full_name=:f, phone_verified=TRUE WHERE id=:i"),
               {"p": body.phone, "f": body.full_name, "i": str(user.id)})
    role = db.execute(_t("SELECT id FROM roles WHERE code='client' LIMIT 1")).first()
    if role:
        rcols = {r[0] for r in db.execute(_t("SELECT column_name FROM information_schema.columns WHERE table_name='user_roles'"))}
        rd = {"user_id": str(user.id), "role_id": str(role[0]), "assigned_at": _dtn.now(_tzn.utc)}
        if "id" in rcols:
            rd["id"] = str(_uuid.uuid4())
        db.execute(_t("INSERT INTO user_roles (" + ",".join(rd) + ") VALUES (" + ",".join(":" + k for k in rd) + ") ON CONFLICT DO NOTHING"), rd)
    cli = db.execute(_t("SELECT id FROM clients WHERE right(regexp_replace(phone,'\D','','g'),10)=:p LIMIT 1"), {"p": norm}).first()
    if cli:
        db.execute(_t("UPDATE clients SET user_id=:u WHERE id=:c"),
                   {"u": str(user.id), "c": str(cli[0])})
        if body.email:
            db.execute(_t("UPDATE clients SET email=:e WHERE id=:c AND (email IS NULL OR email='')"),
                       {"e": body.email, "c": str(cli[0])})
    else:
        parts = body.full_name.split(None, 1)
        db.execute(_t("INSERT INTO clients (id, first_name, last_name, phone, email, gender, birth_date, "
                      "client_category, status, is_active, user_id, created_at, updated_at) "
                      "VALUES (:i,:fn,:ln,:p,:e,'НЕ_УКАЗАН',:bd,'ADULT','ACTIVE',TRUE,:u, now(), now())"),
                   {"i": str(_uuid.uuid4()), "fn": parts[0][:60],
                    "ln": (parts[1] if len(parts) > 1 else "")[:60],
                    "p": body.phone, "e": body.email,
                    "bd": (str(body.birth_year) + "-01-01") if body.birth_year else None,
                    "u": str(user.id)})
    db.commit()
    token = svc.create_user_access_token(user)
    try:
        from app.api.v1.auth import _issue_refresh_token
        refresh = _issue_refresh_token(db, user.id)
    except Exception:
        refresh = None
    return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "expires_in": 1800}
