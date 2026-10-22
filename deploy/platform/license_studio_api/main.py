import os, json, base64, secrets, datetime as dt
from fastapi import FastAPI, HTTPException
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEY_PATH = os.environ.get("LICENSE_PRIVATE_KEY_PATH", "/run/secrets/license_private_key")
app = FastAPI(title="FitIntel License Studio API", docs_url=None, redoc_url=None)

def _load_priv():
    data = open(KEY_PATH, "rb").read()
    return serialization.load_pem_private_key(data, password=None)

def make_key(priv, plan, days, max_clients, club, club_id, temp_password=""):
    """Копия make_key из tools/license_studio/license_studio.py + club_id.
    Формат: FIPRO-<raw>.<sig>, пароль внутри подписанного payload."""
    if not temp_password:
        temp_password = secrets.token_urlsafe(9)[:12]
    exp = (dt.date.today() + dt.timedelta(days=days)).isoformat()
    payload = {"plan": plan, "exp": exp, "max_clients": max_clients,
               "club": club, "club_id": club_id, "rnd": secrets.token_hex(4),
               "superadmin_login": "SuperAdmin", "temp_password": temp_password}
    raw = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(priv.sign(raw.encode())).decode().rstrip("=")
    return "FIPRO-" + raw + "." + sig, temp_password, exp

@app.get("/health")
def health():
    return {"ok": True, "key_loaded": os.path.exists(KEY_PATH)}

@app.post("/issue")
def issue(body: dict):
    club = str(body.get("club") or "").strip()
    club_id = str(body.get("club_id") or club).strip()
    if not club:
        raise HTTPException(400, "club required")
    if not os.path.exists(KEY_PATH):
        raise HTTPException(500, "license_private_key secret not mounted")
    plan = str(body.get("plan") or "Start")
    try:
        days = int(body.get("days"))
        maxc = int(body.get("max_clients", 50))
    except Exception:
        raise HTTPException(400, "days (int) required, max_clients (int)")
    if days < 1 or days > 3660:
        raise HTTPException(400, "days out of range 1..3660")
    priv = _load_priv()
    key, pw, exp = make_key(priv, plan, days, maxc, club, club_id,
                            str(body.get("temp_password") or ""))
    return {"ok": True, "license_key": key, "temp_password": pw, "plan": plan,
            "exp": exp, "days": days, "max_clients": maxc,
            "club": club, "club_id": club_id}
