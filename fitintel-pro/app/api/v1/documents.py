# app/api/v1/documents.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/templates")
def list_templates(
    current_user=Depends(require_permission("documents.read")),
    db: Session = Depends(get_db),
):
    """Шаблоны документов"""
    return {
        "items": [
            {"id": "contract_standard", "name": "Договор оказания услуг (стандартный)", "type": "contract"},
            {"id": "contract_vip", "name": "Договор VIP", "type": "contract"},
            {"id": "consent_personal", "name": "Согласие на обработку ПДн", "type": "consent"},
            {"id": "medical_clearance", "name": "Медицинская справка", "type": "medical"},
            {"id": "cancel_request", "name": "Заявление на расторжение", "type": "request"},
        ]
    }


@router.get("/client/{client_id}")
def client_documents(
    client_id: UUID,
    current_user=Depends(require_permission("documents.read")),
    db: Session = Depends(get_db),
):
    """Документы клиента"""
    from app.models.client import Client
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return {
        "client_id": str(client_id),
        "documents": [
            {"type": "contract", "status": "signed", "signed_at": "2026-04-01"},
            {"type": "consent", "status": "signed", "signed_at": "2026-04-01"},
        ]
    }


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_document(
    payload: dict,
    current_user=Depends(require_permission("documents.create")),
    db: Session = Depends(get_db),
):
    """Сгенерировать документ из шаблона"""
    import uuid
    from app.db.base import utc_now
    doc_id = uuid.uuid4()
    return {
        "id": str(doc_id),
        "template_id": payload.get("template_id"),
        "client_id": payload.get("client_id"),
        "status": "generated",
        "download_url": f"/api/v1/documents/{doc_id}/download",
        "created_at": utc_now().isoformat(),
    }


@router.get("/{doc_id}/download")
def download_document(
    doc_id: UUID,
    current_user=Depends(require_permission("documents.read")),
):
    """Скачать документ (PDF)"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(f"PDF document {doc_id} placeholder")

from fastapi import HTTPException
