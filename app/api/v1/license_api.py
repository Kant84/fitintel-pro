"""License validation + limits (pairs with License Studio)."""
import os, json, hmac, hashlib, base64, logging
from datetime import date, datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()

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

def _secret():
    s = os.environ.get("LICENSE_SECRET", "").strip()
    if not s:
        try:
            for line in open(".env", encoding="utf-8", errors="ignore"):
                if line.startswith("LICENSE_SECRET="):
                    s = line.split("=", 1)[1].strip()
        except Exception:
            pass
    return s

def _validate(key):
    secret = _secret()
    if not secret:
        return {"valid": False, "reason": "LICENSE_SECRET не задан на сервере"}
    try:
        token = key.replace("FIPRO-", "").replace("-", "").strip()
        raw, sig = token.rsplit(".", 1)
        good = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:20].upper()
        if not hmac.compare_digest(good, sig):
            return {"valid": False, "reason": "invalid signature"}
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode())
        payload["valid"] = datetime.strptime(payload["exp"], "%Y-%m-%d").date() >= date.today()
        if not payload["valid"]:
            payload["reason"] = "Истекла " + payload["exp"]
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
    import traceback
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
        "valid": True,
        "plan": v.get("plan"),
        "expires": v.get("exp"),
        "club": v.get("club"),
        "max_clients": limit,
        "clients_used": used,
        "clients_remaining": max(limit - used, 0),
        "within_limit": used <= limit,
        "usage_percent": round(used / limit * 100, 1) if limit else 0,
    }


# === E66: license activation + enforcement mode ===
from pydantic import BaseModel as _BM

class ModeIn(_BM):
    mode: str = "soft"  # soft | hard

def _ensure_state():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS license_state (
            id INT PRIMARY KEY, key TEXT, mode VARCHAR(8) DEFAULT 'soft',
            updated_at TIMESTAMP DEFAULT NOW())"""))

@router.post("/license/activate")
def activate(body: KeyIn):
    v = _validate(body.key)
    if not v.get("valid"):
        return v
    _ensure_state()
    with _eng().begin() as c:
        c.execute(text("""INSERT INTO license_state (id, key, mode, updated_at)
            VALUES (1, :k, 'soft', NOW())
            ON CONFLICT (id) DO UPDATE SET key=EXCLUDED.key, updated_at=EXCLUDED.updated_at"""),
            {"k": body.key})
    return {"activated": True, "plan": v.get("plan"), "expires": v.get("exp"), "max_clients": v.get("max_clients")}

@router.get("/license/current")
def current():
    return current_limit_status()

@router.post("/license/mode")
def set_mode(body: ModeIn):
    _ensure_state()
    with _eng().begin() as c:
        c.execute(text("UPDATE license_state SET mode=:m WHERE id=1"), {"m": "hard" if body.mode == "hard" else "soft"})
    return {"ok": True, "mode": body.mode}

def current_limit_status():
    try:
        _ensure_state()
        with _eng().connect() as c:
            row = c.execute(text("SELECT key, mode FROM license_state WHERE id=1")).first()
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
                "usage_percent": round(used / limit * 100, 1) if limit else 0}
    except Exception as e:
        return {"activated": False, "error": str(e)}

def license_block_check():
    """Возвращает dict с block=True, если создание клиента надо запретить (hard mode + переполнение)."""
    st = current_limit_status()
    if st.get("activated") and not st.get("within_limit") and st.get("mode") == "hard":
        return {"block": True, "used": st.get("clients_used"), "limit": st.get("max_clients")}
    return {"block": False, "over_limit": st.get("activated") and not st.get("within_limit")}
