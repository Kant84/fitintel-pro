# W5: публичный конфиг мини-приложения (брендинг из «Коммерция → White-label»)
from fastapi import APIRouter

from app.api.v1.club_params import get_param

router = APIRouter()


@router.get("/miniapp/config")
def miniapp_config() -> dict:
    return {
        "club_name": get_param("WL.CLUB_NAME", None) or get_param("CLUB_NAME", "Клуб"),
        "slogan": get_param("WL.SLOGAN", "") or "",
        "logo_url": get_param("WL.LOGO_URL", "") or "",
        "accent": get_param("WL.COLOR_ACCENT", "#00f0ff") or "#00f0ff",
    }