# app/models/commercial.py
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    base_price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(String(20), default="monthly")
    max_clients = Column(Integer)
    max_trainers = Column(Integer)
    max_clubs = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")


class PlanModule(Base):
    __tablename__ = "plan_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), nullable=False)
    module_code = Column(String(50), nullable=False)
    module_name = Column(String(100))
    price_addon = Column(Numeric(10, 2), default=0)
    is_included = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default="now()")


class ClubSubscription(Base):
    __tablename__ = "club_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    plan_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), default="active")
    trial_ends_at = Column(TIMESTAMP)
    current_period_start = Column(TIMESTAMP)
    current_period_end = Column(TIMESTAMP)
    next_billing_amount = Column(Numeric(10, 2))
    auto_renew = Column(Boolean, default=True)
    payment_method = Column(String(20))
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")


class WhiteLabelConfig(Base):
    __tablename__ = "white_label_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    app_name = Column(String(100))
    logo_url = Column(String(500))
    primary_color = Column(String(7), default="#1F4E78")
    secondary_color = Column(String(7), default="#4CAF50")
    favicon_url = Column(String(500))
    custom_css = Column(Text)
    domain = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")
