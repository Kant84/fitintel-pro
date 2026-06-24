# app/models/feature_flag.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class FlagScope(str, enum.Enum):
    SYSTEM = "system"
    MODULE = "module"
    TENANT = "tenant"
    USER = "user"
    CANARY = "canary"

class FlagType(str, enum.Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    JSON = "json"

class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    flag_key = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    flag_type = Column(SQLEnum(FlagType), default=FlagType.BOOLEAN, nullable=False)
    default_value = Column(JSON, nullable=False, default=False)
    target_value = Column(JSON, nullable=True)
    scope = Column(SQLEnum(FlagScope), default=FlagScope.SYSTEM, nullable=False)
    target_id = Column(Integer, nullable=True)  # tenant_id или user_id
    conditions = Column(JSON, nullable=True)  # {start_date, end_date, percentage, roles, min_version, required_flags}
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    changed_by = Column(String(255), nullable=True)

    # Отношения
    audit_logs = relationship("FeatureFlagAudit", back_populates="flag", cascade="all, delete-orphan")
    dependencies = relationship("FeatureFlagDependency", foreign_keys="FeatureFlagDependency.flag_id", back_populates="flag")

class FeatureFlagTenantOverride(Base):
    __tablename__ = "feature_flag_tenant_overrides"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, nullable=False, index=True)
    target_value = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    changed_by = Column(String(255), nullable=True)

class FeatureFlagUserOverride(Base):
    __tablename__ = "feature_flag_user_overrides"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    target_value = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    changed_by = Column(String(255), nullable=True)

class FeatureFlagAudit(Base):
    __tablename__ = "feature_flag_audit"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, CHECK
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_by = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flag = relationship("FeatureFlag", back_populates="audit_logs")

class FeatureFlagDependency(Base):
    __tablename__ = "feature_flag_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    requires_flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)

    flag = relationship("FeatureFlag", foreign_keys=[flag_id], back_populates="dependencies")
    required_flag = relationship("FeatureFlag", foreign_keys=[requires_flag_id])
