from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.enums import AlertType

class VideoAlertBase(BaseModel):
    camera_id: str = Field(...)
    alert_type: AlertType
    confidence: Optional[float] = Field(None, ge=0, le=1)
    snapshot: Optional[str] = None
    

class VideoAlertCreate(VideoAlertBase):
    pass

class VideoAlertResponse(VideoAlertBase):
    id: str
    is_false_positive: bool
    reviewed_by: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True

class VideoAlertReviewRequest(BaseModel):
    is_false_positive: bool
    reviewed_by: Optional[int] = Field(None, gt=0)