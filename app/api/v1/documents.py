# app/api/v1/documents.py
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import require_permission
from app.db.session import get_db
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


# ============================================================
# ШАБЛОНЫ
# ============================================================

@router.get("/templates")
def list_templates(
    current_user=Depends(require_permission("documents.read")),
    service: DocumentService = Depends(get_service),
):
    """Шаблоны документов"""
    return {"items": service.list_templates()}


# ============================================================
# CRUD
# ============================================================

@router.get("/client/{client_id}")
def client_documents(
    client_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(require_permission("documents.read")),
    service: DocumentService = Depends(get_service),
):
    """Документы клиента"""
    return service.list_client_documents(client_id, offset, limit)


@router.get("/")
def list_all_documents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    doc_type: str | None = None,
    status: str | None = None,
    current_user=Depends(require_permission("documents.read")),
    service: DocumentService = Depends(get_service),
):
    """Все документы"""
    return service.list_all_documents(offset, limit, doc_type, status)


# ============================================================
# ГЕНЕРАЦИЯ И СКАЧИВАНИЕ
# ============================================================

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_document(
    payload: dict,
    current_user=Depends(require_permission("documents.create")),
    service: DocumentService = Depends(get_service),
):
    """Сгенерировать PDF документ из шаблона"""
    from uuid import UUID as UUIDType
    template_id = payload.get("template_id")
    client_id = UUIDType(payload.get("client_id"))
    extra = payload.get("extra_data", {})
    return service.generate_pdf(template_id, client_id, current_user.id, extra)


@router.get("/{doc_id}/download")
def download_document(
    doc_id: UUID,
    current_user=Depends(require_permission("documents.read")),
    service: DocumentService = Depends(get_service),
):
    """Скачать PDF документ"""
    return service.download_pdf(doc_id)


@router.get("/{doc_id}/preview")
def preview_document(
    doc_id: UUID,
    current_user=Depends(require_permission("documents.read")),
    service: DocumentService = Depends(get_service),
):
    """Просмотр PDF (inline)"""
    return service.preview_pdf(doc_id)


# ============================================================
# ПОДПИСЬ
# ============================================================

@router.post("/{doc_id}/sign")
def sign_document(
    doc_id: UUID,
    current_user=Depends(require_permission("documents.update")),
    service: DocumentService = Depends(get_service),
):
    """Подписать документ электронно"""
    return service.sign_document(doc_id, current_user.id)
