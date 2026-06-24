# app/api/v1/trainers.py
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.schemas.trainer import (
    TrainerProfileCreate, TrainerProfileUpdate, TrainerProfileResponse,
    TrainerScheduleCreate, TrainerScheduleUpdate, TrainerScheduleResponse,
    TrainerBookingCreate, TrainerBookingUpdate, TrainerBookingResponse,
    AttendanceLogCreate, AttendanceLogResponse,
    TrainerSaleCreate, TrainerSaleResponse,
    TrainerKpiResponse, TrainerDashboardResponse
)
from app.services.trainer_service import TrainerService


router = APIRouter(prefix="/trainers", tags=["Trainers"])


# ========== PROFILE ==========
@router.post("/profiles", response_model=TrainerProfileResponse, status_code=201)
async def create_trainer_profile(
    data: TrainerProfileCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("trainers.create"))
):
    """Создать профиль тренера (требуется право trainers.create)"""
    service = TrainerService(db)
    # Проверяем, нет ли уже профиля
    existing = service.get_profile_by_user(data.user_id)
    if existing:
        raise HTTPException(400, "Trainer profile already exists for this user")
    return service.create_profile(data)


@router.get("/profiles", response_model=List[TrainerProfileResponse])
async def list_trainers(
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("trainers.read"))
):
    """Список тренеров"""
    service = TrainerService(db)
    return service.list_trainers(is_active)


@router.get("/profiles/me", response_model=TrainerProfileResponse)
async def get_my_profile(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Мой профиль тренера"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return profile


@router.get("/profiles/{trainer_id}", response_model=TrainerProfileResponse)
async def get_trainer_profile(
    trainer_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("trainers.read"))
):
    """Профиль тренера по ID"""
    service = TrainerService(db)
    profile = service.get_profile(trainer_id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return profile


@router.patch("/profiles/me", response_model=TrainerProfileResponse)
async def update_my_profile(
    data: TrainerProfileUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Обновить свой профиль"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return service.update_profile(profile.id, data)


@router.patch("/profiles/{trainer_id}", response_model=TrainerProfileResponse)
async def update_trainer_profile(
    trainer_id: UUID,
    data: TrainerProfileUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("trainers.update"))
):
    """Обновить профиль тренера (админ)"""
    service = TrainerService(db)
    profile = service.update_profile(trainer_id, data)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return profile


# ========== SCHEDULE ==========
@router.post("/schedules", response_model=TrainerScheduleResponse, status_code=201)
async def create_schedule(
    data: TrainerScheduleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("schedules.create"))
):
    """Создать расписание тренера"""
    service = TrainerService(db)
    return service.create_schedule(data)


@router.get("/schedules", response_model=List[TrainerScheduleResponse])
async def get_trainer_schedule(
    trainer_id: UUID = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("schedules.read"))
):
    """Расписание тренера за период"""
    service = TrainerService(db)
    return service.get_trainer_schedule(trainer_id, start_date, end_date)


@router.get("/schedules/today", response_model=List[TrainerScheduleResponse])
async def get_today_schedule(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Моё расписание на сегодня (для тренера)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return service.get_today_schedule(profile.id)


@router.patch("/schedules/{schedule_id}", response_model=TrainerScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    data: TrainerScheduleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("schedules.update"))
):
    """Обновить расписание"""
    service = TrainerService(db)
    schedule = service.update_schedule(schedule_id, data)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("schedules.delete"))
):
    """Удалить расписание"""
    service = TrainerService(db)
    if not service.delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return None


# ========== BOOKINGS ==========
@router.post("/bookings", response_model=TrainerBookingResponse, status_code=201)
async def create_booking(
    data: TrainerBookingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("bookings.create"))
):
    """Записать клиента на тренировку"""
    service = TrainerService(db)
    try:
        return service.create_booking(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/bookings/client/{client_id}", response_model=List[TrainerBookingResponse])
async def get_client_bookings(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("bookings.read"))
):
    """Записи клиента"""
    service = TrainerService(db)
    return service.get_client_bookings(client_id)


@router.patch("/bookings/{booking_id}", response_model=TrainerBookingResponse)
async def update_booking(
    booking_id: UUID,
    data: TrainerBookingUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("bookings.update"))
):
    """Обновить запись"""
    service = TrainerService(db)
    booking = service.update_booking(booking_id, data)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


# ========== ATTENDANCE ==========
@router.post("/attendance", response_model=AttendanceLogResponse, status_code=201)
async def log_attendance(
    data: AttendanceLogCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Отметить посещение (тренер)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(403, "Only trainers can log attendance")
    return service.log_attendance(profile.id, data)


@router.get("/attendance/today", response_model=List[AttendanceLogResponse])
async def get_today_attendance(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Посещения за сегодня (тренер)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(403, "Only trainers can view attendance")
    return service.get_trainer_attendance(profile.id, date.today())


# ========== SALES ==========
@router.post("/sales", response_model=TrainerSaleResponse, status_code=201)
async def create_sale(
    data: TrainerSaleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Оформить продажу из зала (тренер)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(403, "Only trainers can create sales")
    # Подставляем trainer_id из профиля
    data.trainer_id = profile.id
    return service.create_sale(data)


@router.get("/sales/today", response_model=List[TrainerSaleResponse])
async def get_today_sales(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Продажи за сегодня (тренер)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(403, "Only trainers can view sales")
    return service.get_today_sales(profile.id)


# ========== KPI / DASHBOARD ==========
@router.get("/dashboard", response_model=TrainerDashboardResponse)
async def get_trainer_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Личный кабинет тренера (дашборд)"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")
    return service.get_dashboard(profile.id)


@router.get("/kpi/{year_month}", response_model=TrainerKpiResponse)
async def get_trainer_kpi(
    year_month: str,  # format: 2026-06
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """KPI тренера за месяц"""
    service = TrainerService(db)
    profile = service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(404, "Trainer profile not found")

    kpi = service.calculate_kpi(profile.id, year_month)
    if not kpi:
        raise HTTPException(404, "KPI not found")
    return kpi
