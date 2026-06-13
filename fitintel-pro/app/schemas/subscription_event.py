from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    subscription_id: UUID
    from_status: str | None = None
    to_status: str
    reason: str | None = None
    actor_user_id: UUID | None = None
    created_at: datetime


class SubscriptionEventListResponse(BaseModel):
    items: list[SubscriptionEventResponse]
    count: int