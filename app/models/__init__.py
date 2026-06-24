# app/models/__init__.py

# Core models
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission
from app.models.audit import AuditLog

# CRM
from app.models.client import Client
from app.models.client_event import ClientEvent
from app.models.tariff import Tariff
from app.models.subscription import Subscription
from app.models.subscription_event import SubscriptionEvent

# Access & Visits
from app.models.visit import Visit
from app.models.access_log import AccessLog
from app.models.access_cache import AccessCache
from app.models.credential import Credential
from app.models.locker import Locker
from app.models.locker_session import LockerSession
from app.models.locker_privilege import LockerPrivilege

# Finance
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.cash_desk_session import CashDeskSession
from app.models.cash_operation import CashOperation

# Devices & Hardware
from app.models.device import Device

# Documents & Marketing
from app.models.document import Document
from app.models.marketing_campaign import MarketingCampaign

# Gamification & Online Training
from app.models.gamification_level import GamificationLevel
from app.models.online_session import OnlineSession

# Chat
from app.models.chat import ChatRoom, ChatMessage

# === ДОБАВИТЬ В app/models/__init__.py ===
from app.models.feature_flag import (
    FeatureFlag, FeatureFlagTenantOverride, FeatureFlagUserOverride,
    FeatureFlagAudit, FeatureFlagDependency
)
# Face ID + License (v1.3.0)
from app.models.face_id import (
    FaceTemplate,
    FaceRecognitionLog,
    EmployeeShift,
    License,
    LicenseActivation,
)
from app.models.service import Service, ServiceBooking
from app.models.dynamic_qr import DynamicQRCode
from app.models.video_alert import VideoAlert
from app.models.analytics import AnalyticsDaily
