# W5: публичный конфиг мини-приложения + локальный QR
import urllib.parse as _up

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, Response

from app.api.v1.club_params import get_param

router = APIRouter()


@router.get("/miniapp/config")
def miniapp_config() -> dict:
    return {
        "club_name": get_param("WL.CLUB_NAME", None) or get_param("CLUB_NAME", "Клуб"),
        "slogan": get_param("WL.SLOGAN", "") or "",
        "logo_url": get_param("WL.LOGO_URL", "") or "",
        "accent": get_param("WL.COLOR_ACCENT", "#00f0ff") or "#00f0ff",
        "support_phone": get_param("WL.SUPPORT_PHONE", "") or "",
        "support_email": get_param("WL.SUPPORT_EMAIL", "") or "",
        "hours": get_param("WL.HOURS", "Будни 8:30–23:00") or "",
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
        return RedirectResponse(
            "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data="
            + _up.quote(data))
