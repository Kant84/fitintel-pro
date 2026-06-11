# app/repositories/document_repository.py

from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.document import Document


class DocumentRepository:
    """Репозиторий документов (договоры, согласия, справки)"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, doc_id: UUID) -> Document | None:
        return self.db.execute(
            select(Document).where(Document.id == doc_id)
        ).scalar_one_or_none()

    def list_by_client(
        self,
        client_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[Document], int]:
        query = select(Document).where(Document.client_id == client_id).order_by(desc(Document.created_at))
        count = self.db.execute(
            select(Document).where(Document.client_id == client_id)
        ).scalars().all()
        docs = list(self.db.execute(query.offset(offset).limit(limit)).scalars().all())
        return docs, len(count)

    def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        doc_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        query = select(Document)
        if doc_type:
            query = query.where(Document.doc_type == doc_type)
        if status:
            query = query.where(Document.status == status)
        query = query.order_by(desc(Document.created_at))
        all_docs = list(self.db.execute(query).scalars().all())
        paginated = all_docs[offset:offset + limit]
        return paginated, len(all_docs)

    def create(self, doc: Document) -> Document:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update(self, doc: Document) -> Document:
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_client_and_type(self, client_id: UUID, doc_type: str) -> Document | None:
        return self.db.execute(
            select(Document)
            .where(Document.client_id == client_id)
            .where(Document.doc_type == doc_type)
            .order_by(desc(Document.created_at))
        ).scalars().first()
