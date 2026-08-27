
"""E15-SKUD: Интеграция с ITCService — терминалы СКУД, онлайн-замки, солярий, аквапарк."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.credential_service import CredentialService
from app.services.client_service import ClientService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/skud", tags=["SKUD / ITC Integration"])
security = HTTPBasic(auto_error=False)


# ==========================================================
# СХЕМЫ ЗАПРОСОВ / ОТВЕТОВ (формат ITCService)
# ==========================================================

class CheckAccessRequest(BaseModel):
    device_id: str = Field(..., description="IP устройства")
    client_card: str = Field(..., description="UID RFID-карты")
    request_id: str = Field(..., description="UUID запроса")
    qr: Optional[str] = Field(None, description="QR-код")
    minutes: Optional[str] = Field("0", description="Минуты для солярия")
    client_id: Optional[str] = Field(None, description="UUID клиента")


class CheckAccessResponse(BaseModel):
    client_id: Optional[str] = None
    text: str = "Проходите"
    grant_access: int = 1
    text_full: str = "Доступ разрешен."
    withoutface: bool = False


class OLockCheckAccessRequest(BaseModel):
    card: str = Field(..., description="UID клиентской карты")
    group: str = Field(..., description="man / women / safe")


class OLockCheckAccessResponse(BaseModel):
    success: bool = True
    error: Optional[str] = None
    grant_access: bool = True
    text_full: str = "Доступ есть"
    allow_rent: bool = True
    quantity: int = 3


class AquaCheckAccessRequest(BaseModel):
    card: str = Field(..., description="UID клиентской карты")
    device_id: Optional[str] = Field(None, description="IP устройства")


class AquaCheckAccessResponse(BaseModel):
    Code: int = 201
    Description: Optional[str] = None
    Data: Optional[str] = None
    DataObj: dict = {
        "FullName": "", "TariffName": "", "Credit": 0,
        "Balance": 0, "Limit": 0, "TimeIn": "", "TimeOut": "", "TimeLeft": ""
    }


class SolarCheckAccessRequest(BaseModel):
    client_card: str
    client_id: Optional[str] = None
    device_id: str
    request_id: str


class SolarCheckAccessResponse(BaseModel):
    minute_purchase: int = 0
    grant_access: int = 0
    text: str = ""
    text_full: str = ""
    minute_price: int = 50
    credit_allow: bool = False


class EventRequest(BaseModel):
    device_id: str
    client_card: str
    request_id: str
    qr: Optional[str] = None
    minutes: Optional[str] = "0"
    client_id: Optional[str] = None


class EventResponse(BaseModel):
    request_id: str
    success: bool = True
    error: Optional[str] = None


class CheckAccessErrorRequest(BaseModel):
    device_id: str
    client_card: str
    request_id: str
    client_id: Optional[str] = None
    last_faces: List[str] = []
    error_text: str


# ==========================================================
# BASIC AUTH (для ITCService)
# ==========================================================

def verify_basic(credentials: HTTPBasicCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Basic Auth required")
    if credentials.username != "itc" or credentials.password != "itc_secret_2026":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials


# ==========================================================
# CHECKACCESS — проход через терминал СКУД
# ==========================================================

@router.post("/checkaccess", response_model=CheckAccessResponse)
def check_access(
    payload: CheckAccessRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    cred_service = CredentialService(db)
    credential = cred_service.get_by_value(payload.client_card)

    if not credential or credential.credential_type != "RFID":
        return CheckAccessResponse(
            text="Карта не найдена", grant_access=0,
            text_full="Доступ запрещен. Карта не зарегистрирована.", withoutface=False,
        )

    client_id = str(credential.client_id)
    sub_service = SubscriptionService(db)
    active_sub = sub_service.get_active_by_client(client_id)

    if not active_sub:
        return CheckAccessResponse(
            client_id=client_id, text="Нет активного абонемента",
            grant_access=0, text_full="Доступ запрещен. Нет активного абонемента.", withoutface=False,
        )

    if active_sub.end_date and active_sub.end_date < date.today():
        return CheckAccessResponse(
            client_id=client_id, text="Абонемент просрочен",
            grant_access=0, text_full="Доступ запрещен. Абонемент просрочен.", withoutface=False,
        )

    return CheckAccessResponse(
        client_id=client_id, text="Проходите", grant_access=1,
        text_full="Доступ разрешен.", withoutface=False,
    )


# ==========================================================
# OLOCK_CHECKACCESS — онлайн-замки (шкафчики)
# ==========================================================

@router.post("/olock_checkaccess", response_model=OLockCheckAccessResponse)
def olock_check_access(
    payload: OLockCheckAccessRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    cred_service = CredentialService(db)
    credential = cred_service.get_by_value(payload.card)

    if not credential:
        return OLockCheckAccessResponse(
            success=True, grant_access=False, text_full="Карта не найдена",
            allow_rent=False, quantity=0,
        )

    return OLockCheckAccessResponse(
        success=True, grant_access=True, text_full="Доступ есть",
        allow_rent=True, quantity=3,
    )


# ==========================================================
# AQUA_CHECKACCESS — аквапарк / инфотерминал
# ==========================================================

@router.post("/aqua_checkaccess", response_model=AquaCheckAccessResponse)
def aqua_check_access(
    payload: AquaCheckAccessRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    cred_service = CredentialService(db)
    credential = cred_service.get_by_value(payload.card)

    if not credential:
        return AquaCheckAccessResponse(Code=404, Description="Карта не найдена")

    client = ClientService(db).get_by_id(str(credential.client_id))
    if not client:
        return AquaCheckAccessResponse(Code=404, Description="Клиент не найден")

    return AquaCheckAccessResponse(
        Code=201,
        DataObj={
            "FullName": client.last_name + " " + client.first_name,
            "TariffName": "Аквапарк",
            "Credit": 0,
            "Balance": 1000,
            "Limit": 5000,
            "TimeIn": "10:00",
            "TimeOut": "22:00",
            "TimeLeft": "12:00",
        }
    )


# ==========================================================
# SOLAR / CHECKACCESS — солярий
# ==========================================================

@router.post("/solar/checkaccess", response_model=SolarCheckAccessResponse)
def solar_check_access(
    payload: SolarCheckAccessRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    cred_service = CredentialService(db)
    credential = cred_service.get_by_value(payload.client_card)

    if not credential:
        return SolarCheckAccessResponse(
            grant_access=0, text="Карта не найдена", text_full="Доступ запрещен",
        )

    return SolarCheckAccessResponse(
        minute_purchase=15, grant_access=1, text="Проходите",
        text_full="Доступ разрешен. Осталось 15 минут.",
        minute_price=50, credit_allow=True,
    )


# ==========================================================
# EVENT — фиксация прохода
# ==========================================================

@router.post("/event", response_model=EventResponse)
def event(
    payload: EventRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    # TODO: записать визит в БД
    return EventResponse(request_id=payload.request_id, success=True)


# ==========================================================
# CHECKACCESS_ERROR — ошибка FaceID
# ==========================================================

@router.post("/checkaccess_error")
def checkaccess_error(
    payload: CheckAccessErrorRequest,
    db: Session = Depends(get_db),
    auth=Depends(verify_basic),
):
    return {"success": True, "error": None}


# ==========================================================
# HEALTH CHECK для ITCService
# ==========================================================

@router.get("/health_check")
def health_check():
    return {"status": "ok", "service": "FitIntel-SKUD"}
