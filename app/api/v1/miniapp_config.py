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
    cli = db.execute(_t("SELECT id FROM clients WHERE right(regexp_replace(phone,'\\D','','g'),10)=:p LIMIT 1"), {"p": norm}).first()
    if not cli:
        raise _HE(404, "Клиент с таким телефоном не найден. Сначала зарегистрируйтесь на ресепшене клуба")
    canon = "+7" + norm
    from app.services.auth_service import AuthService
    svc = AuthService(db)
    user = svc.create_user(norm, body.password, body.email)
    db.execute(_t("UPDATE users SET phone=:p, full_name=:f, phone_verified=TRUE WHERE id=:i"),
               {"p": canon, "f": body.full_name, "i": str(user.id)})
    role = db.execute(_t("SELECT id FROM roles WHERE code='client' LIMIT 1")).first()
    if role:
        rneed = {r[0]: r[1] for r in db.execute(_t("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='user_roles' AND is_nullable='NO' AND column_default IS NULL"))}
        rd = {"user_id": str(user.id), "role_id": str(role[0])}
        for _col, _dt in rneed.items():
            if _col in rd:
                continue
            if _col == "id":
                rd[_col] = str(_uuid.uuid4())
            elif _dt.startswith("timestamp") or _col.endswith("_at"):
                rd[_col] = _dtn.now(_tzn.utc)
            elif _dt == "boolean":
                rd[_col] = False
            elif _dt.startswith("int") or _dt.startswith("numeric"):
                rd[_col] = 0
            else:
                rd[_col] = ""
        db.execute(_t("INSERT INTO user_roles (" + ",".join(rd) + ") VALUES (" + ",".join(":" + k for k in rd) + ") ON CONFLICT DO NOTHING"), rd)
    db.execute(_t("UPDATE clients SET user_id=:u WHERE id=:c"),
               {"u": str(user.id), "c": str(cli[0])})
    if body.email:
        db.execute(_t("UPDATE clients SET email=:e WHERE id=:c AND (email IS NULL OR email='')"),
                   {"e": body.email, "c": str(cli[0])})
    db.commit()
    token = svc.create_user_access_token(user)
    try:
        from app.api.v1.auth import _issue_refresh_token
        refresh = _issue_refresh_token(db, user.id)
    except Exception:
        refresh = None
    return {"access_token": token, "refresh_token": refresh, "token_type": "bearer", "expires_in": 1800}


# === W6: MAX Bridge — вход без пароля, регистрация без кода ===
import hashlib as _hl
import hmac as _hm
import json as _js
import re as _re2
import time as _tm
import urllib.parse as _up


class BridgeAuthIn(_BM):
    initData: str


class BridgeRegIn(_BM):
    initData: str
    full_name: str = _FL(min_length=3, max_length=200)
    birth_year: int | None = None
    password: str = _FL(min_length=8, max_length=128)
    phone: str | None = None
    contact_hash: str | None = None
    contact_auth_date: str | None = None


def _max_token(db) -> str:
    r = db.execute(_t("SELECT bot_token FROM max_bot_settings WHERE id=1")).first()
    return (r[0] if r else "") or ""


def _validate_init(init_data: str, bot_token: str):
    try:
        pairs = [x.split("=", 1) for x in str(init_data or "").split("&") if "=" in x]
        if sum(1 for k, _ in pairs if k == "hash") != 1:
            return None
        d = {}
        for k, v in pairs:
            if k in d:
                return None
            d[k] = v
        orig = d.pop("hash")
        dec = {k: _up.unquote(v) for k, v in d.items()}
        launch = "\n".join("%s=%s" % (k, dec[k]) for k in sorted(dec))
        secret = _hm.new(b"WebAppData", bot_token.encode(), _hl.sha256).digest()
        calc = _hm.new(secret, launch.encode(), _hl.sha256).hexdigest()
        if not _hm.compare_digest(calc, orig):
            return None
        ad = int(dec.get("auth_date") or 0)
        if not ad or abs(_tm.time() - ad) > 3600:
            return None
        return _js.loads(dec.get("user") or "{}")
    except Exception:
        return None


def _issue_token(uid: str) -> dict:
    from datetime import timedelta as _td
    from app.core.security import create_access_token
    tok = create_access_token(subject=uid, expires_delta=_td(minutes=60 * 24 * 7))
    return {"access_token": tok, "token_type": "bearer", "expires_in": 60 * 24 * 7}


@router.post("/max-bridge/auth")
def max_bridge_auth(body: BridgeAuthIn, db: _S = _Dep(_gdb)):
    tok = _max_token(db)
    if not tok:
        raise _HE(503, "Бот MAX не настроен")
    mu = _validate_init(body.initData, tok)
    if not mu:
        raise _HE(401, "Подпись MAX не подтверждена")
    muid = str(mu.get("id") or "")
    row = db.execute(_t(
        "SELECT c.user_id FROM max_bot_bindings b JOIN clients c "
        "ON replace(b.client_id,'-','')=replace(cast(c.id as text),'-','') "
        "WHERE b.max_user_id=:m LIMIT 1"), {"m": muid}).first()
    if row and row[0]:
        acc = db.execute(_t("SELECT 1 FROM users WHERE id=:i"), {"i": str(row[0])}).first()
        if acc:
            return _issue_token(str(row[0]))
    return {"registered": False, "max_user_id": muid,
            "first_name": mu.get("first_name") or "", "last_name": mu.get("last_name") or ""}


@router.post("/max-bridge/register")
def max_bridge_register(body: BridgeRegIn, db: _S = _Dep(_gdb)):
    tok = _max_token(db)
    mu = _validate_init(body.initData, tok) if tok else None
    if not mu:
        raise _HE(401, "Подпись MAX не подтверждена")
    muid = str(mu.get("id") or "")
    phone = None
    if body.phone and body.contact_hash and body.contact_auth_date:
        p = body.phone.lstrip("+")
        s = "authDate=%s\nphone=%s\nuserId=%s" % (body.contact_auth_date, p, muid)
        calc = _hm.new(tok.encode(), s.encode(), _hl.sha256).hexdigest()
        if _hm.compare_digest(calc, body.contact_hash):
            phone = body.phone
    if not phone:
        raise _HE(400, "Подтвердите номер телефона в MAX (кнопка в форме)")
    norm = _re2.sub(r"\D", "", phone)[-10:]
    canon = "+7" + norm
    cli = db.execute(_t("SELECT id FROM clients WHERE right(regexp_replace(phone,'\\D','','g'),10)=:p LIMIT 1"), {"p": norm}).first()
    if not cli:
        raise _HE(404, "Клиент с таким телефоном не найден. Сначала зарегистрируйтесь на ресепшене клуба")
    if db.execute(_t("SELECT 1 FROM users WHERE username=:u OR phone=:p LIMIT 1"), {"u": norm, "p": canon}).first():
        raise _HE(409, "Аккаунт уже существует — войдите")
    from app.services.auth_service import AuthService
    svc = AuthService(db)
    user = svc.create_user(norm, body.password, None)
    db.execute(_t("UPDATE users SET phone=:p, full_name=:f, phone_verified=TRUE WHERE id=:i"),
               {"p": canon, "f": body.full_name, "i": str(user.id)})
    role = db.execute(_t("SELECT id FROM roles WHERE code='client' LIMIT 1")).first()
    if role:
        rneed = {r[0]: r[1] for r in db.execute(_t("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='user_roles' AND is_nullable='NO' AND column_default IS NULL"))}
        rd = {"user_id": str(user.id), "role_id": str(role[0])}
        for _col, _dt in rneed.items():
            if _col in rd:
                continue
            rd[_col] = str(_uuid.uuid4()) if _col == "id" else (_dtn.now(_tzn.utc) if (_dt.startswith("timestamp") or _col.endswith("_at")) else (False if _dt == "boolean" else (0 if (_dt.startswith("int") or _dt.startswith("numeric")) else "")))
        db.execute(_t("INSERT INTO user_roles (" + ",".join(rd) + ") VALUES (" + ",".join(":" + k for k in rd) + ") ON CONFLICT DO NOTHING"), rd)
    db.execute(_t("UPDATE clients SET user_id=:u WHERE id=:c"), {"u": str(user.id), "c": str(cli[0])})
    db.execute(_t("INSERT INTO max_bot_bindings (max_user_id, client_id) VALUES (:m,:c) "
                  "ON CONFLICT (max_user_id) DO UPDATE SET client_id=:c"),
               {"m": int(muid), "c": str(cli[0]).replace("-", "")})
    db.commit()
    return _issue_token(str(user.id))


# === W6: профиль для мини-приложения (учётка + карточка клиента) ===
from app.api.dependencies import get_current_user as _gcu


class MeUpdate(_BM):
    full_name: str | None = None
    birth_year: int | None = None
    email: str | None = None


@router.post("/miniapp/me")
def miniapp_me_update(body: MeUpdate, current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    uid = str(current.id)
    if body.full_name:
        db.execute(_t("UPDATE users SET full_name=:f WHERE id=:i"), {"f": body.full_name.strip()[:200], "i": uid})
        parts = body.full_name.split(None, 1)
        db.execute(_t("UPDATE clients SET first_name=:fn, last_name=:ln WHERE user_id=:u"),
                   {"fn": parts[0][:60], "ln": (parts[1] if len(parts) > 1 else "")[:60], "u": uid})
    if body.birth_year:
        db.execute(_t("UPDATE clients SET birth_date=:b WHERE user_id=:u"),
                   {"b": "%s-01-01" % int(body.birth_year), "u": uid})
    if body.email is not None:
        db.execute(_t("UPDATE clients SET email=:e WHERE user_id=:u"), {"e": body.email.strip() or None, "u": uid})
        db.execute(_t("UPDATE users SET email=:e WHERE id=:i AND (email IS NULL OR email='')"),
                   {"e": body.email.strip() or None, "i": uid})
    db.commit()
    return miniapp_me(current, db)


@router.get("/miniapp/me")
def miniapp_me(current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    uid = str(current.id)
    u = db.execute(_t("SELECT username, email, phone, full_name FROM users WHERE id=:i"), {"i": uid}).first()
    c = db.execute(_t("SELECT id, first_name, last_name, birth_date, phone, email FROM clients WHERE user_id=:u LIMIT 1"), {"u": uid}).first()
    return {
        "id": uid,
        "username": u[0] if u else None,
        "email": (u[1] if u else None) or (c[5] if c else None),
        "phone": (u[2] if u else None) or (c[4] if c else None),
        "full_name": (u[3] if u else None) or (((c[1] or "") + " " + (c[2] or "")).strip() if c else None),
        "birth_date": str(c[3])[:10] if c and c[3] else None,
        "client_id": str(c[0]) if c else None,
    }


# === W6: баланс и бонусы клиента ===
@router.get("/miniapp/wallet")
def miniapp_wallet(current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    uid = str(current.id)
    c = db.execute(_t("SELECT id FROM clients WHERE user_id=:u LIMIT 1"), {"u": uid}).first()
    out = {"balance": None, "bonuses": None}
    if not c:
        return out
    cid = str(c[0])
    tabs = {r[0] for r in db.execute(_t("SELECT table_name FROM information_schema.tables WHERE table_name IN ('wallets','wallet')"))}
    if tabs:
        t = tabs.pop()
        row = db.execute(_t(f"SELECT * FROM {t} WHERE client_id::text=:c LIMIT 1"), {"c": cid}).mappings().first()
        if row:
            d = dict(row)
            for k, v in d.items():
                kl = k.lower()
                if out["balance"] is None and "balance" in kl and "bonus" not in kl:
                    try:
                        out["balance"] = float(v)
                    except Exception:
                        pass
                if out["bonuses"] is None and "bonus" in kl:
                    try:
                        out["bonuses"] = float(v)
                    except Exception:
                        pass
    if out["bonuses"] is None:
        g = db.execute(_t("SELECT current_xp FROM gamification_levels WHERE client_id::text=:c LIMIT 1"), {"c": cid}).first()
        out["bonuses"] = float(g[0]) if g and g[0] is not None else None
    return out


# === W6: пополнение кошелька ===
class TopupIn(_BM):
    amount: float


def _wallet_cfg(db):
    from app.api.v1.club_params import get_param
    try:
        return {"provider": get_param("WALLET_PAY_PROVIDER", "test") or "test",
                "min": float(get_param("WALLET_TOPUP_MIN", "100") or 100),
                "bonus_percent": float(get_param("WALLET_BONUS_PERCENT", "5") or 5)}
    except Exception:
        return {"provider": "test", "min": 100.0, "bonus_percent": 5.0}


@router.get("/miniapp/wallet/config")
def wallet_config(db: _S = _Dep(_gdb)):
    return _wallet_cfg(db)


def _wallet_credit(db, client_id: str, amount: float, bonus_percent: float) -> dict:
    w = db.execute(_t("SELECT id, balance FROM wallets WHERE client_id::text=:c"), {"c": client_id}).first()
    if w:
        wid = str(w[0])
        db.execute(_t("UPDATE wallets SET balance=balance+:a, updated_at=now() WHERE id=:i"), {"a": amount, "i": wid})
        bal = float(w[1] or 0) + amount
    else:
        wid = str(_uuid.uuid4())
        db.execute(_t("INSERT INTO wallets (id, client_id, balance, frozen_balance, currency, created_at, updated_at) VALUES (:i,:c,:a,0,'RUB', now(), now())"),
                   {"i": wid, "c": client_id, "a": amount})
        bal = amount
    rneed = {r[0]: r[1] for r in db.execute(_t("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='wallet_transactions' AND is_nullable='NO' AND column_default IS NULL"))}
    td = {"id": str(_uuid.uuid4()), "wallet_id": wid, "client_id": client_id, "amount": amount,
          "type": "topup", "transaction_type": "topup", "description": "Пополнение через приложение",
          "balance_before": round(bal - amount, 2), "balance_after": round(bal, 2),
          "created_at": _dtn.now(_tzn.utc), "updated_at": _dtn.now(_tzn.utc)}
    for col, dt in rneed.items():
        if col in td:
            continue
        if col == "id":
            td[col] = str(_uuid.uuid4())
        elif col == "wallet_id":
            td[col] = wid
        elif col == "client_id":
            td[col] = client_id
        elif col == "balance_before":
            td[col] = round(bal - amount, 2)
        elif col == "balance_after":
            td[col] = round(bal, 2)
        elif dt.startswith("timestamp") or col.endswith("_at"):
            td[col] = _dtn.now(_tzn.utc)
        elif dt == "boolean":
            td[col] = False
        elif dt.startswith(("int", "numeric", "float", "double")):
            td[col] = 0
        else:
            td[col] = "topup"
    td = {k: v for k, v in td.items() if k in rneed or k in ("type",)}
    tcols = {r[0] for r in db.execute(_t("SELECT column_name FROM information_schema.columns WHERE table_name='wallet_transactions'"))}
    td = {k: v for k, v in td.items() if k in tcols}
    db.execute(_t("INSERT INTO wallet_transactions (" + ",".join(td) + ") VALUES (" + ",".join(":" + k for k in td) + ")"), td)
    db.commit()
    return {"balance": round(bal, 2)}


@router.post("/miniapp/wallet/topup")
def wallet_topup(body: TopupIn, current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    cfg = _wallet_cfg(db)
    amount = round(float(body.amount), 2)
    if amount < cfg["min"]:
        raise _HE(422, "Минимальная сумма пополнения: %s руб." % int(cfg["min"]))
    c = db.execute(_t("SELECT id FROM clients WHERE user_id=:u LIMIT 1"), {"u": str(current.id)}).first()
    if not c:
        raise _HE(404, "Карточка клиента не найдена")
    cid = str(c[0])
    if cfg["provider"] == "test":
        r = _wallet_credit(db, cid, amount, cfg["bonus_percent"])
        bonus = award_bonus(db, cid, "topup", amount)
        if bonus <= 0:
            bonus = _add_xp(db, cid, round(amount * cfg["bonus_percent"] / 100.0, 2))
        return {"ok": True, "provider": "test", "balance": r["balance"], "bonuses_added": bonus}
    if cfg["provider"] == "yookassa":
        from app.services.yookassa_service import YooKassaService
        pay = YooKassaService(db).create_payment(
            amount, "Пополнение кошелька", "https://fixintel.ru/static/miniapp/index.html",
            metadata={"wallet_topup": "1", "client_id": cid, "bonus_percent": str(cfg["bonus_percent"])})
        url = ((pay or {}).get("confirmation") or {}).get("confirmation_url") or (pay or {}).get("payment_url")
        return {"ok": True, "provider": "yookassa", "payment_url": url, "payment_id": (pay or {}).get("id")}
    raise _HE(503, "Провайдер '%s' пока не подключен" % cfg["provider"])


def _ensure_bonus_rules(db):
    db.execute(_t("CREATE TABLE IF NOT EXISTS bonus_rules ("
                  "id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                  "category VARCHAR(20) NOT NULL DEFAULT 'ALL',"
                  "event VARCHAR(30) NOT NULL,"
                  "mode VARCHAR(10) NOT NULL DEFAULT 'fix',"
                  "value NUMERIC(12,2) NOT NULL DEFAULT 0,"
                  "active BOOLEAN DEFAULT TRUE,"
                  "created_at TIMESTAMPTZ DEFAULT now())"))
    db.commit()


def _add_xp(db, client_id, xp):
    if xp <= 0:
        return 0.0
    g = db.execute(_t("SELECT id FROM gamification_levels WHERE client_id::text=:c"), {"c": str(client_id)}).first()
    if g:
        db.execute(_t("UPDATE gamification_levels SET current_xp=current_xp+:b, updated_at=now() WHERE id=:i"), {"b": xp, "i": str(g[0])})
    else:
        gcols = {r[0] for r in db.execute(_t("SELECT column_name FROM information_schema.columns WHERE table_name='gamification_levels'"))}
        gd = {k: v for k, v in {"id": str(_uuid.uuid4()), "client_id": client_id, "current_xp": xp, "level": 1,
                                "xp_to_next": 100, "total_visits": 0, "total_workout_minutes": 0, "streak_days": 0,
                                "max_streak_days": 0, "achievements_count": 0,
                                "created_at": _dtn.now(_tzn.utc), "updated_at": _dtn.now(_tzn.utc)}.items() if k in gcols}
        db.execute(_t("INSERT INTO gamification_levels (" + ",".join(gd) + ") VALUES (" + ",".join(":" + k for k in gd) + ")"), gd)
    db.commit()
    return xp


def award_bonus(db, client_id, event, amount=0):
    _ensure_bonus_rules(db)
    c = db.execute(_t("SELECT client_category FROM clients WHERE id::text=:c"), {"c": str(client_id)}).first()
    cat = ((c[0] if c else None) or "").upper()
    rows = db.execute(_t(
        "SELECT mode, value FROM bonus_rules WHERE event=:e AND active=TRUE "
        "AND (category='ALL' OR category=:cat) "
        "ORDER BY CASE WHEN category='ALL' THEN 1 ELSE 0 END"),
        {"e": str(event).lower()[:30], "cat": cat}).fetchall()
    total = 0.0
    for mode, val in rows:
        v = float(val or 0)
        total += round(amount * v / 100.0, 2) if str(mode) == "percent" else v
    if total <= 0:
        return 0.0
    return _add_xp(db, client_id, round(total, 2))


class RuleIn(_BM):
    category: str = "ALL"
    event: str
    mode: str = "fix"
    value: float = 0


@router.get("/bonus-rules")
def bonus_rules_list(current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    _ensure_bonus_rules(db)
    rows = db.execute(_t("SELECT id, category, event, mode, value, active FROM bonus_rules ORDER BY created_at")).fetchall()
    return {"items": [{"id": str(r[0]), "category": r[1], "event": r[2], "mode": r[3],
                       "value": float(r[4]), "active": bool(r[5])} for r in rows]}


@router.post("/bonus-rules")
def bonus_rules_add(body: RuleIn, current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    _ensure_bonus_rules(db)
    rid = str(_uuid.uuid4())
    db.execute(_t("INSERT INTO bonus_rules (id, category, event, mode, value, active) VALUES (:i,:c,:e,:m,:v,TRUE)"),
               {"i": rid, "c": body.category.upper()[:20], "e": body.event.lower()[:30],
                "m": body.mode.lower()[:10], "v": body.value})
    db.commit()
    return {"ok": True, "id": rid}


@router.delete("/bonus-rules/{rid}")
def bonus_rules_del(rid: str, current=_Dep(_gcu), db: _S = _Dep(_gdb)):
    db.execute(_t("DELETE FROM bonus_rules WHERE id::text=:r"), {"r": str(rid)})
    db.commit()
    return {"ok": True}
