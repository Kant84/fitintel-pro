from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.services.face_id_service import FaceIDService
from app.core.security import require_role

router = APIRouter(prefix="/api/v1/face-id", tags=["Face ID"])

class FaceRecognitionRequest(BaseModel):
    face_encoding: List[float]
    terminal_id: str
    terminal_location: Optional[str] = None

class FaceRecognitionResponse(BaseModel):
    access_granted: bool
    reason: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_type: Optional[str] = None

class FaceRegisterRequest(BaseModel):
    user_id: int
    user_type: str
    face_encoding: List[float]
    photo_path: Optional[str] = None
    quality_score: Optional[float] = None

class ShiftCreateRequest(BaseModel):
    employee_id: int
    shift_start: datetime
    shift_end: datetime
    location: Optional[str] = None
    notes: Optional[str] = None

@router.post("/verify", response_model=FaceRecognitionResponse)
async def verify_face(request: FaceRecognitionRequest, db: Session = Depends(get_db)):
    """Терминал отправляет вектор лица и получает решение о доступе"""
    service = FaceIDService(db)
    granted, reason, info = service.recognize_and_grant_access(
        request.face_encoding, request.terminal_id, request.terminal_location
    )
    return FaceRecognitionResponse(
        access_granted=granted, reason=reason,
        user_id=info.get("user_id"), user_name=info.get("name"), user_type=info.get("type")
    )

@router.post("/register")
async def register_face(request: FaceRegisterRequest, db: Session = Depends(get_db),
                        current_user = Depends(require_role(["admin", "manager"]))):
    """Регистрация нового биометрического шаблона"""
    service = FaceIDService(db)
    template = service.register_face(
        request.user_id, request.user_type, request.face_encoding,
        request.photo_path, request.quality_score
    )
    return {"id": template.id, "is_primary": template.is_primary, "status": "created"}

@router.get("/logs")
async def get_logs(terminal_id: Optional[str] = None, limit: int = 100,
                   db: Session = Depends(get_db),
                   current_user = Depends(require_role(["admin", "manager"]))):
    """Логи распознавания лиц"""
    from app.models.face_id import FaceRecognitionLog
    query = db.query(FaceRecognitionLog)
    if terminal_id:
        query = query.filter(FaceRecognitionLog.terminal_id == terminal_id)
    logs = query.order_by(FaceRecognitionLog.created_at.desc()).limit(limit).all()
    return logs

@router.post("/shifts")
async def create_shift(request: ShiftCreateRequest, db: Session = Depends(get_db),
                       current_user = Depends(require_role(["admin", "manager"]))):
    """Создание смены сотрудника"""
    from app.models.face_id import EmployeeShift
    shift = EmployeeShift(
        employee_id=request.employee_id, shift_start=request.shift_start,
        shift_end=request.shift_end, location=request.location, notes=request.notes,
        status="scheduled", created_by=current_user.id
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return {"id": shift.id, "status": "scheduled"}

@router.patch("/shifts/{shift_id}/start")
async def start_shift(shift_id: int, db: Session = Depends(get_db),
                      current_user = Depends(require_role(["admin", "manager", "employee"]))):
    """Начало смены (сотрудник отмечается)"""
    from app.models.face_id import EmployeeShift
    shift = db.query(EmployeeShift).filter(EmployeeShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Смена не найдена")
    shift.status = "active"
    shift.actual_start = datetime.utcnow()
    db.commit()
    return {"id": shift.id, "status": "active"}

@router.patch("/shifts/{shift_id}/end")
async def end_shift(shift_id: int, db: Session = Depends(get_db),
                    current_user = Depends(require_role(["admin", "manager", "employee"]))):
    """Окончание смены"""
    from app.models.face_id import EmployeeShift
    shift = db.query(EmployeeShift).filter(EmployeeShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Смена не найдена")
    shift.status = "completed"
    shift.actual_end = datetime.utcnow()
    db.commit()
    return {"id": shift.id, "status": "completed"}

@router.get("/shifts/active")
async def get_active_shifts(db: Session = Depends(get_db),
                            current_user = Depends(require_role(["admin", "manager"]))):
    """Список активных смен"""
    from app.models.face_id import EmployeeShift
    now = datetime.utcnow()
    shifts = db.query(EmployeeShift).filter(
        EmployeeShift.status == "active",
        EmployeeShift.shift_start <= now,
        EmployeeShift.shift_end >= now
    ).all()
    return shifts
