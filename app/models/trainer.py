# app/models/trainer.py
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, Date, Time, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class TrainerProfile(Base):
    __tablename__ = "trainer_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    specialization = Column(String(100))
    bio = Column(Text)
    photo_url = Column(String(500))
    rate_per_hour = Column(Numeric(10, 2), default=0)
    commission_percent = Column(Numeric(5, 2), default=0)
    is_active = Column(Boolean, default=True)
    max_clients_per_day = Column(Integer, default=8)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")

    user = relationship("User", back_populates="trainer_profile")
    schedules = relationship("TrainerSchedule", back_populates="trainer", cascade="all, delete-orphan")
    sales = relationship("TrainerSale", back_populates="trainer", cascade="all, delete-orphan")
    kpi_records = relationship("TrainerKpiMonthly", back_populates="trainer", cascade="all, delete-orphan")


class TrainerSchedule(Base):
    __tablename__ = "trainer_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id = Column(UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False)
    schedule_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    type = Column(String(20))
    title = Column(String(200))
    description = Column(Text)
    hall_id = Column(UUID(as_uuid=True))  # FK to halls.id — removed for compatibility
    max_slots = Column(Integer, default=1)
    booked_slots = Column(Integer, default=0)
    status = Column(String(20), default="scheduled")
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")

    trainer = relationship("TrainerProfile", back_populates="schedules")
    # hall relationship removed — use hall_id only
    bookings = relationship("TrainerBooking", back_populates="schedule", cascade="all, delete-orphan")


class TrainerBooking(Base):
    __tablename__ = "trainer_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("trainer_schedules.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="booked")
    attended_at = Column(TIMESTAMP)
    cancelled_at = Column(TIMESTAMP)
    cancel_reason = Column(Text)
    created_at = Column(TIMESTAMP, default="now()")

    schedule = relationship("TrainerSchedule", back_populates="bookings")
    client = relationship("Client")
    attendance_logs = relationship("TrainerAttendanceLog", back_populates="booking", cascade="all, delete-orphan")


class TrainerAttendanceLog(Base):
    __tablename__ = "trainer_attendance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("trainer_bookings.id", ondelete="CASCADE"), nullable=False)
    trainer_id = Column(UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)
    notes = Column(Text)
    logged_at = Column(TIMESTAMP, default="now()")
    created_at = Column(TIMESTAMP, default="now()")

    booking = relationship("TrainerBooking", back_populates="attendance_logs")
    trainer = relationship("TrainerProfile")
    client = relationship("Client")


class TrainerSale(Base):
    __tablename__ = "trainer_sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id = Column(UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    product_id = Column(UUID(as_uuid=True))  # FK to products.id — removed for compatibility
    product_name = Column(String(200))
    amount = Column(Numeric(10, 2), nullable=False)
    commission_amount = Column(Numeric(10, 2), default=0)
    sale_type = Column(String(20))
    payment_method = Column(String(20))
    status = Column(String(20), default="completed")
    created_at = Column(TIMESTAMP, default="now()")

    trainer = relationship("TrainerProfile", back_populates="sales")
    client = relationship("Client")
    # product relationship removed — use product_id only


class TrainerKpiMonthly(Base):
    __tablename__ = "trainer_kpi_monthly"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trainer_id = Column(UUID(as_uuid=True), ForeignKey("trainer_profiles.id", ondelete="CASCADE"), nullable=False)
    year_month = Column(String(7), nullable=False)
    sessions_count = Column(Integer, default=0)
    sessions_personal = Column(Integer, default=0)
    sessions_group = Column(Integer, default=0)
    clients_total = Column(Integer, default=0)
    clients_new = Column(Integer, default=0)
    clients_retained = Column(Integer, default=0)
    clients_churned = Column(Integer, default=0)
    revenue_from_sessions = Column(Numeric(12, 2), default=0)
    revenue_from_sales = Column(Numeric(12, 2), default=0)
    commission_total = Column(Numeric(12, 2), default=0)
    salary_total = Column(Numeric(12, 2), default=0)
    rate_applied = Column(Numeric(10, 2), default=0)
    bonus_new_clients = Column(Numeric(10, 2), default=0)
    bonus_retention = Column(Numeric(10, 2), default=0)
    bonus_sales = Column(Numeric(10, 2), default=0)
    penalty_no_show = Column(Numeric(10, 2), default=0)
    penalty_late_cancel = Column(Numeric(10, 2), default=0)
    base_salary = Column(Numeric(12, 2), default=0)
    total_bonus = Column(Numeric(12, 2), default=0)
    total_penalty = Column(Numeric(12, 2), default=0)
    net_salary = Column(Numeric(12, 2), default=0)
    rating_avg = Column(Numeric(3, 2), default=0)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")

    trainer = relationship("TrainerProfile", back_populates="kpi_records")
