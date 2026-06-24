from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date

from app.api.dependencies import get_db, get_current_user
from app.models.service import Service, ServiceBooking
from app.models.client import Client
from app.schemas.service import (
    ServiceCreate, ServiceUpdate, ServiceResponse,
    ServiceBookingCreate, ServiceBookingResponse,
    ServiceAvailabilityResponse
)
from app.schemas.enums import ServiceCategory
from app.api.dependencies import require_permission

router = APIRouter(prefix="/services", tags=["Услуги (E19)"])

@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)

async def create_service(service: ServiceCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_service = Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("", response_model=List[ServiceResponse])

async def list_services(category: Optional[ServiceCategory] = None, is_active: Optional[bool] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Service)
    if category:
        query = query.filter(Service.category == category.value)
    if is_active is not None:
        query = query.filter(Service.is_active == is_active)
    if search:
        query = query.filter(Service.name.ilike(f"%{search}%"))
    return query.order_by(Service.name).all()

@router.get("/{service_id}", response_model=ServiceResponse)

async def get_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return service

@router.put("/{service_id}", response_model=ServiceResponse)

async def update_service(service_id: int, service_update: ServiceUpdate, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    for field, value in service_update.dict(exclude_unset=True).items():
        setattr(service, field, value)
    service.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(service)
    return service

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)

async def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    db.delete(service)
    db.commit()
    return None

@router.get("/{service_id}/availability", response_model=ServiceAvailabilityResponse)

async def get_availability(service_id: int, check_date: Optional[date] = None, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    check_date = check_date or date.today()
    schedule = service.schedule or {}
    time_slots = schedule.get("time_slots", [])
    bookings = db.query(ServiceBooking).filter(
        and_(ServiceBooking.service_id == service_id, func.date(ServiceBooking.booking_date) == check_date, ServiceBooking.status.in_(["BOOKED", "COMPLETED"]))
    ).all()
    slots = []
    for slot in time_slots:
        slot_time = slot.get("time", "")
        capacity = slot.get("capacity", service.max_capacity)
        booked = len([b for b in bookings if b.booking_date.strftime("%H:%M") == slot_time])
        slots.append({"time": slot_time, "capacity": capacity, "booked": booked, "available": max(0, capacity - booked), "is_full": booked >= capacity})
    return ServiceAvailabilityResponse(service_id=service_id, service_name=service.name, date=check_date, available_slots=slots, is_available=any(s["available"] > 0 for s in slots))

@router.post("/{service_id}/book", response_model=ServiceBookingResponse, status_code=status.HTTP_201_CREATED)

async def book_service(service_id: int, booking: ServiceBookingCreate, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    client = db.query(Client).filter(Client.id == booking.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    existing = db.query(ServiceBooking).filter(
        and_(ServiceBooking.client_id == booking.client_id, func.date(ServiceBooking.booking_date) == func.date(booking.booking_date), ServiceBooking.status == "BOOKED")
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="У вас уже есть запись на это время")
    current_bookings = db.query(ServiceBooking).filter(
        and_(ServiceBooking.service_id == service_id, func.date(ServiceBooking.booking_date) == func.date(booking.booking_date), ServiceBooking.status.in_(["BOOKED", "COMPLETED"]))
    ).count()
    if current_bookings >= service.max_capacity:
        raise HTTPException(status_code=409, detail="Мест нет")
    db_booking = ServiceBooking(client_id=booking.client_id, service_id=service_id, booking_date=booking.booking_date, status="BOOKED")
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@router.post("/bookings/{booking_id}/cancel", response_model=ServiceBookingResponse)

async def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if booking.status != "BOOKED":
        raise HTTPException(status_code=409, detail="Нельзя отменить выполненную запись")
    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    return booking
