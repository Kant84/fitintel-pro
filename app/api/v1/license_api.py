""""License validation + limits (Ed25519, pairs with License Studio).
На сервере ТОЛЬКО публичный ключ (app/core/license_public.pem) — он не секрет.
Приватный ключ существует только у владельца (License Studio).
Пароль клиента живёт ВНУТРИ подписанного ключа — activate ставит ровно его."""
import os, json, base64, logging
from datetime import date, datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)
router = APIRouter()

_PUB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "core", "license_public.pem")
_PUB = None


def _pub():
    global _PUB
    if _PUB is None:
        _PUB = load_pem_public_key(open(_PUB_PATH, "rb").read())
    return _PUB


_engine = None
def _eng():
    global _engine
    if _engine is None:
        for mod in ("app.db.session", "app.core.database", "app.database"):
            try:
                m = __import__(mod, fromlist=["engine"])
                _engine = getattr(m, "engine")
                break
            except Exception:
                continue
    if _engine is None:
        raise RuntimeError("DB engine not found")
    return _engine


def _validate(key):
    try:
        token = key.replace("FIPRO-", "").strip()
        raw, sig = token.rsplit(".", 1)
        try:
            _pub().verify(base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)),
                          raw.encode())
        except InvalidSignature:
            return {"valid": False, "reason": "Подпись не совпадает — ключ недействителен"}
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode())
        payload["valid"] = datetime.strptime(payload["exp"], "%Y-%m-%d").date() >= date.today()
        if not payload["valid"]:
            payload["reason"] = "Истёк " + payload["exp"]
        return payload
    except Exception as e:
        return {"valid": False, "reason": str(e)}


def _clients_count():
    for tbl in ("clients", "users"):
        try:
            with _eng().connect() as c:
                return int(c.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar() or 0)
        except Exception:
            continue
    return 0


class KeyIn(BaseModel):
    key: str


@router.post("/license/validate")
def validate(body: KeyIn):
    return _validate(body.key)


@router.get("/license/limits")
def limits(license_key: str = Query(...)):
    try:
        return _limits_inner(license_key)
    except Exception:
        return {"valid": False, "reason": "bad key format"}


def _limits_inner(license_key):
    v = _validate(license_key)
    if not v.get("valid"):
        return v
    used = _clients_count()
    limit = int(v.get("max_clients") or 0)
    return {
        "valid": True, "plan": v.get("plan"), "expires": v.get("exp"),
        "club": v.get("club"), "max_clients": limit, "clients_used": used,
        "clients_remaining": max(limit - used, 0),
        "within_limit": used <= limit,
        "usage_percent": round(used / limit * 100, 1) if limit else 0,
    }


class ModeIn(BaseModel):
    mode: str = "soft"


def _ensure_state():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS license_state (
            id INT PRIMARY KEY, key TEXT, mode VARCHAR(8) DEFAULT 'soft',
            temp_password TEXT, superadmin_login TEXT DEFAULT 'SuperAdmin',
            is_first_login BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT NOW())"""))
        c.execute(text(
            "ALTER TABLE license_state ADD COLUMN IF NOT EXISTS install_fp VARCHAR(64)"))


def _sync_superadmin_password(c, temp_pass: str, superadmin_login: str):
    """Создаёт или обновляет владельца лицензии внутри общей транзакции."""
    import uuid
    from datetime import datetime, timezone
    from app.core.security import get_password_hash

    login = (superadmin_login or "").strip()
    if not login or len(login) > 100:
        raise ValueError("Некорректный superadmin_login в лицензии")
    if not isinstance(temp_pass, str) or len(temp_pass) < 8:
        raise ValueError("Временный пароль лицензии должен содержать минимум 8 символов")

    ids = c.execute(text(
        "SELECT id FROM users WHERE lower(username)=lower(:login)"
    ), {"login": login}).scalars().all()
    if len(ids) > 1:
        raise RuntimeError("Найдено несколько учётных записей владельца лицензии")

    params = {
        "ph": get_password_hash(temp_pass),
        "id": ids[0] if ids else None,
    }
    if ids:
        result = c.execute(text(
            "UPDATE users SET password_hash=:ph, failed_login_count=0, "
            "locked_until=NULL, is_active=TRUE, is_superuser=TRUE, "
            "is_verified=TRUE WHERE id=:id"
        ), params)
        if result.rowcount != 1:
            raise RuntimeError("Не удалось обновить владельца лицензии")
        return

    now = datetime.now(timezone.utc)
    c.execute(text(
        "INSERT INTO users (id, username, password_hash, is_active, "
        "is_superuser, is_verified, is_fired, failed_login_count, "
        "created_at, updated_at) VALUES (:id, :login, :ph, TRUE, TRUE, "
        "TRUE, FALSE, 0, :now, :now)"
    ), {
        "id": str(uuid.uuid4()),
        "login": login,
        "ph": params["ph"],
        "now": now,
    })


def _fingerprint():
    """Отпечаток установки — одноразовость лицензии (привязка к серверу)."""
    import hashlib
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            mid = open(p).read().strip()
            if mid:
                return hashlib.sha256(mid.encode()).hexdigest()[:32]
        except Exception:
            continue
    return None

@router.post("/license/activate")
def activate(body: KeyIn):
    v = _validate(body.key)
    if not v.get("valid"):
        return v
    temp_pass = v.get("temp_password")
    if not temp_pass:
        import string, secrets as _s
        temp_pass = ''.join(_s.choice(string.ascii_letters + string.digits)
                            for _ in range(10))
    sadmin = v.get("superadmin_login") or "SuperAdmin"
    _ensure_state()
    fp = _fingerprint()
    with _eng().connect() as c:
        existing = c.execute(
            text("SELECT key, install_fp FROM license_state WHERE id=1")).first()
    if existing and existing[0] == body.key:
        # Тот же сервер и ключ: повторная активация также восстанавливает
        # отсутствующего владельца лицензии после старой ошибки установки.
        with _eng().begin() as c:
            _sync_superadmin_password(c, temp_pass, sadmin)
        return {"activated": True, "already_active": True,
                "plan": v.get("plan"), "superadmin_login": sadmin,
                "temp_password": temp_pass}
    if existing and existing[1] and fp and existing[1] != fp:
        return {"activated": False,
                "reason": "Лицензия уже активирована на другом сервере. "
                          "Для переноса выпустите новый ключ в License Studio."}
    with _eng().begin() as c:
        c.execute(text(
            "INSERT INTO license_state (id, key, mode, temp_password, superadmin_login, is_first_login, install_fp, updated_at) "
            "VALUES (1, :k, 'soft', :tp, :sa, TRUE, :fp, CURRENT_TIMESTAMP) "
            "ON CONFLICT (id) DO UPDATE SET key=EXCLUDED.key, temp_password=EXCLUDED.temp_password, "
            "superadmin_login=EXCLUDED.superadmin_login, is_first_login=TRUE, "
            "install_fp=EXCLUDED.install_fp, updated_at=CURRENT_TIMESTAMP"),
            {"k": body.key, "tp": temp_pass, "sa": sadmin, "fp": fp})
        _sync_superadmin_password(c, temp_pass, sadmin)
    return {"activated": True, "plan": v.get("plan"), "expires": v.get("exp"),
            "max_clients": v.get("max_clients"),
            "superadmin_login": sadmin, "temp_password": temp_pass,
            "message": f"Лицензия активирована. Первый вход: {sadmin} / {temp_pass}"}


@router.get("/license/current")
def current():
    return current_limit_status()


@router.post("/license/mode")
def set_mode(body: ModeIn):
    _ensure_state()
    with _eng().begin() as c:
        c.execute(text("UPDATE license_state SET mode=:m WHERE id=1"),
                  {"m": "hard" if body.mode == "hard" else "soft"})
    return {"ok": True, "mode": body.mode}


def current_limit_status():
    try:
        _ensure_state()
        with _eng().connect() as c:
            row = c.execute(text(
                "SELECT key, mode, is_first_login, superadmin_login FROM license_state WHERE id=1")).first()
        if not row or not row[0]:
            return {"activated": False}
        v = _validate(row[0])
        if not v.get("valid"):
            return {"activated": False, "reason": v.get("reason")}
        used = _clients_count()
        limit = int(v.get("max_clients") or 0)
        return {"activated": True, "plan": v.get("plan"), "expires": v.get("exp"),
                "mode": row[1], "max_clients": limit, "clients_used": used,
                "within_limit": used <= limit,
                "usage_percent": round(used / limit * 100, 1) if limit else 0,
                "is_first_login": row[2] if len(row) > 2 else True,
                "superadmin_login": row[3] if len(row) > 3 else "SuperAdmin"}
    except Exception as e:
        return {"activated": False, "error": str(e)}


def license_block_check():
    st = current_limit_status()
    if st.get("activated") and not st.get("within_limit") and st.get("mode") == "hard":
        return {"block": True, "used": st.get("clients_used"),
                "limit": st.get("max_clients")}
    return {"block": False,
            "over_limit": st.get("activated") and not st.get("within_limit")}
            
@router.get("/license/status")
def status():
    """ПУБЛИЧНЫЙ статус активации — desktop спрашивает при первом запуске (без токена)."""
    try:
        st = current_limit_status()
        return {"activated": bool(st.get("activated"))}
    except Exception:
        return {"activated": False}          