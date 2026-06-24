# app/schemas/trainer.py
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


# ========== Trainer Profile ==========
class TrainerProfileBase(BaseModel):
    specialization: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    rate_per_hour: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    commission_percent: Decimal = Field(default=Decimal("0"), max_digits=5, decimal_places=2)
    is_active: bool = True
    max_clients_per_day: int = 8


class TrainerProfileCreate(TrainerProfileBase):
    user_id: UUID


class TrainerProfileUpdate(BaseModel):
    specialization: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    rate_per_hour: Optional[Decimal] = None
    commission_percent: Optional[Decimal] = None
    is_active: Optional[bool] = None
    max_clients_per_day: Optional[int] = None


class TrainerProfileResponse(TrainerProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Trainer Schedule ==========
class TrainerScheduleBase(BaseModel):
    schedule_date: date
    start_time: time
    end_time: time
    type: str = Field(..., pattern="^(personal|group|consultation)$")
    title: Optional[str] = None
    description: Optional[str] = None
    hall_id: Optional[UUID] = None
    max_slots: int = 1
    booked_slots: int = 0
    status: str = Field(default="scheduled", pattern="^(scheduled|completed|cancelled|no_show)$")


class TrainerScheduleCreate(TrainerScheduleBase):
    trainer_id: UUID


class TrainerScheduleUpdate(BaseModel):
    schedule_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    hall_id: Optional[UUID] = None
    max_slots: Optional[int] = None
    status: Optional[str] = None


class TrainerScheduleResponse(TrainerScheduleBase):
    id: UUID
    trainer_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Trainer Booking ==========
class TrainerBookingBase(BaseModel):
    schedule_id: UUID
    client_id: UUID
    status: str = Field(default="booked", pattern="^(booked|attended|missed|cancelled_by_client|cancelled_by_trainer)$")


class TrainerBookingCreate(TrainerBookingBase):
    pass


class TrainerBookingUpdate(BaseModel):
    status: Optional[str] = None
    attended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None


class TrainerBookingResponse(TrainerBookingBase):
    id: UUID
    attended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Attendance Log ==========
class AttendanceLogCreate(BaseModel):
    booking_id: UUID
    client_id: UUID
    status: str = Field(..., pattern="^(attended|missed|late|early_leave)$")
    notes: Optional[str] = None


class AttendanceLogResponse(BaseModel):
    id: UUID
    booking_id: UUID
    trainer_id: UUID
    client_id: UUID
    status: str
    notes: Optional[str] = None
    logged_at: datetime

    class Config:
        from_attributes = True


# ========== Trainer Sale ==========
class TrainerSaleBase(BaseModel):
    client_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    product_name: Optional[str] = None
    amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    sale_type: str = Field(..., pattern="^(membership|product|service|package)$")
    payment_method: str = Field(..., pattern="^(cash|card|deposit|sbp)$")


class TrainerSaleCreate(TrainerSaleBase):
    trainer_id: Optional[UUID] = None


class TrainerSaleResponse(TrainerSaleBase):
    id: UUID
    trainer_id: UUID
    commission_amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== KPI ==========
class TrainerKpiResponse(BaseModel):
    id: UUID
    trainer_id: UUID
    year_month: str
    sessions_count: int
    sessions_personal: int
    sessions_group: int
    clients_total: int
    clients_new: int
    clients_retained: int
    clients_churned: int
    revenue_from_sessions: Decimal
    revenue_from_sales: Decimal
    commission_total: Decimal
    salary_total: Decimal
    # E19: Progressive salary
    rate_applied: Decimal
    bonus_new_clients: Decimal
    bonus_retention: Decimal
    bonus_sales: Decimal
    penalty_no_show: Decimal
    penalty_late_cancel: Decimal
    base_salary: Decimal
    total_bonus: Decimal
    total_penalty: Decimal
    net_salary: Decimal
    rating_avg: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Dashboard ==========
class TrainerDashboardResponse(BaseModel):
    trainer_id: UUID
    today_schedules: List[TrainerScheduleResponse]
    today_bookings: int
    today_attended: int
    today_missed: int
    month_sessions: int
    month_revenue: Decimal
    month_commission: Decimal
    clients_total: int
    clients_new_this_month: int
