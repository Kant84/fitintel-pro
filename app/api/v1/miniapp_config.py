# W5: конфиг мини-приложения + локальный QR + отзывы
import urllib.parse as _up
import uuid as _uuid
from datetime import datetime as _dt, timezone as _tz

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import text as _t

from app.api.v1.club_params import get_param
from app.db.session import engine as _e

router = APIRouter()


def _club_cfg():
    try:
        with _e.connect() as c:
            row = c.execute(_t("SELECT about, hours, support_phone, support_email, payments_enabled FROM max_bot_settings WHERE id=1")).first()
    except Exception:
        row = None
    g = lambda i, d="": (row[i] if row and row[i] else d)
    return {"about": g(0), "hours": g(1), "support_phone": g(2), "support_email": g(3),
            "payments_enabled": (bool(row[4]) if row and row[4] is not None else True)}


@router.get("/miniapp/config")
def miniapp_config() -> dict:
    c = _club_cfg()
    return {
        "club_name": get_param("WL.CLUB_NAME", None) or get_param("CLUB_NAME", "Клуб"),
        "slogan": get_param("WL.SLOGAN", "") or "",
        "accent": get_param("WL.COLOR_ACCENT", "#00f0ff") or "#00f0ff",
        "about": c["about"] or (get_param("WL.ABOUT", "") or ""),
        "hours": c["hours"] or "Будни 8:30-23:00",
        "support_phone": c["support_phone"],
        "support_email": c["support_email"],
        "payments_enabled": c["payments_enabled"],
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
