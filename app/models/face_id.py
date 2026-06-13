from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class FaceTemplate(Base):
    __tablename__ = "face_templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_type = Column(String(20), nullable=False, default="client")
    face_encoding = Column(JSON, nullable=False)
    photo_path = Column(String(255), nullable=True)
    quality_score = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user = relationship("User", back_populates="face_templates")
    recognition_logs = relationship("FaceRecognitionLog", back_populates="face_template", cascade="all, delete-orphan")

class FaceRecognitionLog(Base):
    __tablename__ = "face_recognition_logs"
    id = Column(Integer, primary_key=True, index=True)
    face_template_id = Column(Integer, ForeignKey("face_templates.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_type = Column(String(20), nullable=True)
    terminal_id = Column(String(100), nullable=False, index=True)
    terminal_location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    reason = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)
    match_score = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    has_valid_subscription = Column(Boolean, nullable=True)
    has_valid_shift = Column(Boolean, nullable=True)
    is_employee_active = Column(Boolean, nullable=True)
    is_fired = Column(Boolean, nullable=True)
    captured_photo_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    face_template = relationship("FaceTemplate", back_populates="recognition_logs")
    user = relationship("User")

class EmployeeShift(Base):
    __tablename__ = "employee_shifts"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_start = Column(DateTime(timezone=True), nullable=False)
    shift_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="scheduled")
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    employee = relationship("User", foreign_keys=[employee_id], back_populates="shifts")

class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(255), unique=True, nullable=False, index=True)
    owner_name = Column(String(255), nullable=False)
    owner_email = Column(String(255), nullable=False)
    license_type = Column(String(50), nullable=False, default="standard")
    max_users = Column(Integer, nullable=False, default=100)
    max_terminals = Column(Integer, nullable=False, default=5)
    max_clients = Column(Integer, nullable=False, default=1000)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    signature = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    activations = relationship("LicenseActivation", back_populates="license", cascade="all, delete-orphan")

class LicenseActivation(Base):
    __tablename__ = "license_activations"
    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    license = relationship("License", back_populates="activations")
