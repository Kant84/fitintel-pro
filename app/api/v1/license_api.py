"""License validation endpoint (pairs with License Studio)."""
import os, json, hmac, hashlib, base64
from datetime import date, datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class KeyIn(BaseModel):
    key: str

@router.post("/license/validate")
def validate(body: KeyIn):
    secret = os.environ.get("LICENSE_SECRET", "").strip()
    if not secret:
        try:
            for _line in open(".env", encoding="utf-8", errors="ignore"):
                if _line.startswith("LICENSE_SECRET="):
                    secret = _line.split("=", 1)[1].strip()
        except Exception:
            pass
    if not secret:
        return {"valid": False, "reason": "LICENSE_SECRET не задан в .env на сервере"}
    try:
        token = body.key.replace("FIPRO-", "").replace("-", "").strip()
        raw, sig = token.rsplit(".", 1)
        good = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:20].upper()
        if not hmac.compare_digest(good, sig):
            return {"valid": False, "reason": "invalid signature"}
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode())
        payload["valid"] = datetime.strptime(payload["exp"], "%Y-%m-%d").date() >= date.today()
        return payload
    except Exception as e:
        return {"valid": False, "reason": str(e)}
