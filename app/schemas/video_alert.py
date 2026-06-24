from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.enums import AlertType

class VideoAlertBase(BaseModel):
    camera_id: int = Field(..., gt=0)
    alert_type: AlertType
    confidence: Optional[float] = Field(None, ge=0, le=1)
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None

class VideoAlertCreate(VideoAlertBase):
    pass

class VideoAlertResponse(VideoAlertBase):
    id: int
    is_false_positive: bool
    reviewed_by: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True

class VideoAlertReviewRequest(BaseModel):
    is_false_positive: bool
    reviewed_by: int = Field(..., gt=0)