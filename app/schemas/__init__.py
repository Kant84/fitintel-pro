from app.schemas.service import *
from app.schemas.dynamic_qr import *
from app.schemas.video_alert import *

# === ДОБАВИТЬ В app/schemas/__init__.py ===
from app.schemas.feature_flag import (
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureFlagCheckRequest, FeatureFlagCheckResponse,
    FeatureFlagBulkUpdate, FeatureFlagAuditResponse
)