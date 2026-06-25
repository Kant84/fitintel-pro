# app/api/v1/exports.py
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.services.export_service import ExportService
from app.models.export import ExportJob


router = APIRouter(prefix="/exports", tags=["Export"])


# ========== EXPORT JOBS ==========
@router.post("/{entity}", status_code=201)
async def create_export(
    entity: str,  # clients, payments, visits, sales
    background_tasks: BackgroundTasks,
    format: str = Query("xlsx", regex="^(xlsx|csv|json|xml)$"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("exports.create"))
):
    """Создать задачу экспорта"""
    service = ExportService(db)
    
    # Валидация entity
    if entity not in ('clients', 'payments', 'visits', 'sales'):
        raise HTTPException(400, "Invalid entity. Use: clients, payments, visits, sales")
    
    filters = {
        "club_id": club_id,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None
    }
    
    job = service.create_job(club_id, current_user.id, entity, format, filters)
    
    # Запускаем экспорт в фоне
    background_tasks.add_task(service.export, job.id)
    
    return {
        "job_id": str(job.id),
        "entity": entity,
        "format": format,
        "status": "pending",
        "message": "Export started in background"
    }


@router.get("/jobs")
async def list_jobs(
    club_id: int = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(20),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Список задач экспорта"""
    query = db.query(ExportJob).filter(ExportJob.club_id == club_id).order_by(ExportJob.created_at.desc())
    if status:
        query = query.filter(ExportJob.status == status)
    return query.limit(limit).all()


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Статус задачи экспорта"""
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}/download")
async def download_export(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Скачать файл экспорта"""
    from fastapi.responses import FileResponse
    
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != 'completed':
        raise HTTPException(400, f"Export not ready. Status: {job.status}")
    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(404, "File not found")
    
    # Определяем media_type
    media_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv; charset=utf-8',
        'json': 'application/json',
        'xml': 'application/xml'
    }
    
    return FileResponse(
        job.file_path,
        media_type=media_types.get(job.format, 'application/octet-stream'),
        filename=f"fitintel_export_{job.entity}_{job_id}.{job.format}"
    )


# ========== QUICK EXPORT (синхронный) ==========
@router.get("/{entity}/quick")
async def quick_export(
    entity: str,
    format: str = Query("csv", regex="^(xlsx|csv|json|xml)$"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("exports.create"))
):
    """Быстрый экспорт (до 1000 строк, синхронно)"""
    from fastapi.responses import StreamingResponse
    import io
    
    service = ExportService(db)
    
    if entity not in ('clients', 'payments', 'visits', 'sales'):
        raise HTTPException(400, "Invalid entity")
    
    filters = {
        "club_id": club_id,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None
    }
    
    # Создаём job и сразу выполняем
    job = service.create_job(club_id, current_user.id, entity, format, filters)
    filepath = service.export(job.id)
    
    # Читаем файл и возвращаем
    with open(filepath, 'rb') as f:
        content = f.read()
    
    media_types = {
        'csv': 'text/csv; charset=utf-8',
        'json': 'application/json'
    }
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_types.get(format, 'application/octet-stream'),
        headers={
            "Content-Disposition": f'attachment; filename="fitintel_{entity}_{job.id}.{format}"'
        }
    )
