# app/api/v1/client_verification.py
"""
Phone verification API for client registration.

POST /api/v1/clients/verify-phone/request  — request code via MAX push
POST /api/v1/clients/verify-phone/confirm  — confirm code
GET  /api/v1/clients/verify-phone/status   — check status
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrations.max.verification import get_phone_verification_service

router = APIRouter(prefix="/clients/verify-phone", tags=["Phone Verification"])


class PhoneRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number in any format", examples=["+7 (900) 123-45-67"])
    channel: str = Field(default="max", description="Channel: max, sms, auto")


class CodeConfirmRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number")
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit code from push")


class VerifyResponse(BaseModel):
    status: str
    phone: str | None = None
    expires_in: int | None = None
    attempts_left: int | None = None
    channel: str | None = None
    retry_after: int | None = None
    detail: str | None = None


@router.post("/request", response_model=VerifyResponse)
async def request_verification_code(req: PhoneRequest) -> dict[str, Any]:
    """Request verification code sent via MAX push notification."""
    service = get_phone_verification_service()

    if req.channel == "auto":
        result = service.send_code_with_fallback(req.phone_number)
    else:
        result = service.send_code(req.phone_number, send_via=req.channel)

    if result["status"] == "sent":
        return VerifyResponse(
            status="sent",
            phone=result.get("phone"),
            expires_in=result.get("expires_in"),
            attempts_left=result.get("attempts_left"),
            channel=result.get("channel"),
        )
    elif result["status"] == "cooldown":
        return VerifyResponse(
            status="cooldown",
            retry_after=result.get("retry_after"),
            detail=f"Повторный запрос через {result.get('retry_after')} сек",
        )
    else:
        raise HTTPException(status_code=500, detail=result.get("detail", "Failed to send code"))


@router.post("/confirm", response_model=VerifyResponse)
async def confirm_verification_code(req: CodeConfirmRequest) -> dict[str, Any]:
    """Confirm verification code entered by user."""
    service = get_phone_verification_service()
    result = service.verify_code(req.phone_number, req.code)

    if result["status"] == "verified":
        return VerifyResponse(status="verified", phone=result.get("phone"))
    elif result["status"] == "invalid":
        return VerifyResponse(
            status="invalid",
            attempts_left=result.get("attempts_left"),
            detail=f"Неверный код. Осталось попыток: {result.get('attempts_left')}",
        )
    elif result["status"] == "expired":
        raise HTTPException(status_code=410, detail="Код истёк. Запросите новый.")
    elif result["status"] == "max_attempts_exceeded":
        raise HTTPException(status_code=429, detail="Слишком много попыток. Запросите новый код.")
    elif result["status"] == "already_verified":
        return VerifyResponse(status="already_verified", phone=result.get("phone"))
    else:
        raise HTTPException(status_code=400, detail="Unknown status")


@router.get("/status")
async def get_verification_status(phone_number: str) -> dict[str, Any]:
    """Check verification status for a phone number."""
    service = get_phone_verification_service()
    return service.get_status(phone_number)
