# app/integrations/max/__init__.py
"""MAX Messenger integration — push notifications and phone verification."""

from app.integrations.max.service import MAXService
from app.integrations.max.verification import PhoneVerificationService, get_phone_verification_service

__all__ = ["MAXService", "PhoneVerificationService", "get_phone_verification_service"]
