# app/api/v1/documents.py
"""
Documents API E33 — документы по шаблонам (договор абонемента, согласие на
обработку ПДн, медсправка), подписание (простое и ЭП CAdES-эмуляция),
экспорт PDF/DOCX, отправка на email и печать (эмуляция для тестов).
"""

import io
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape as _xesc

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/documents", tags=["Documents E33"])


def _insert(db: Session, table: str, data: dict):
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    cols = {r[0] for r in rows}
    data = {k: v for k, v in data.items() if k in cols and v is not None}
    db.execute(text(
        f"INSERT INTO {table} ({', '.join(data)}) VALUES ({', '.join(':' + k for k in data)})"
    ), data)


def _get_client(db: Session, client_id: str) -> Optional[dict]:
    r = db.execute(text(
        "SELECT id, first_name, last_name, middle_name, phone, email, birth_date "
        "FROM clients WHERE id = :id"
    ), {"id": client_id}).fetchone()
    if not r:
        return None
    full_name = " ".join(p for p in [r[2], r[1], r[3]] if p)
    return {"id": str(r[0]), "full_name": full_name, "phone": r[4] or "",
            "email": r[5] or "", "birth_date": str(r[6] or "")}


def _get_template(db: Session, template_id: Optional[str], code: Optional[str]):
    if template_id:
        return db.execute(text(
            "SELECT id, code, name, content FROM document_templates WHERE id = :v"
        ), {"v": template_id}).fetchone()
    if code:
        return db.execute(text(
            "SELECT id, code, name, content FROM document_templates WHERE code = :v"
        ), {"v": code}).fetchone()
    return None


def _render(content: str, client: dict, data: dict) -> str:
    values = {
        "client_name": client.get("full_name", ""),
        "client_phone": client.get("phone", ""),
        "client_email": client.get("email", ""),
        "birth_date": client.get("birth_date", ""),
        "date": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
    }
    values.update({k: str(v) for k, v in (data or {}).items()})
    out = content or ""
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _pdf_bytes(title: str, content: str) -> bytes:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = [title or ""] + (content or "").split("\n")
    parts = ["BT /F1 12 Tf 50 790 Td"]
    for i, ln in enumerate(lines[:44]):
        safe = esc(ln).encode("latin-1", "replace").decode("latin-1")
        if i == 0:
            parts.append(f"({safe}) Tj")
        else:
            parts.append(f"0 -17 Td ({safe}) Tj")
    parts.append("ET")
    stream = "\n".join(parts)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = "%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n"
    pdf += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF")
    return pdf.encode("latin-1")


def _docx_bytes(title: str, content: str) -> bytes:
    paras = "".join(
        f"<w:p><w:r><w:t>{_xesc(p)}</w:t></w:r></w:p>"
        for p in [title or ""] + (content or "").split("\n")
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paras}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
    return buf.getvalue()


class DocumentCreate(BaseModel):
    type: str
    client_id: str
    template_id: Optional[str] = None
    data: dict = {}


class SignRequest(BaseModel):
    signature: str = ""


class SignEPRequest(BaseModel):
    certificate: str = ""


class EmailRequest(BaseModel):
    email: Optional[str] = None


_DOC_COLS = ("id, client_id, template_id, doc_type, title, content, status, "
             "signed, signed_at, created_at")


def _doc_dict(r):
    return {"document_id": r[0], "client_id": r[1], "template_id": r[2],
            "type": r[3], "title": r[4], "content": r[5], "status": r[6],
            "signed": bool(r[7]), "signed_at": str(r[8]) if r[8] else None,
            "pdf_url": f"/api/v1/documents/{r[0]}/download?format=pdf",
            "created_at": str(r[9]) if r[9] else None}


@router.post("", status_code=201)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    """E33.1/E33.2/E33.8-10 — создание документа по шаблону"""
    if not payload.template_id:
        tpl = _get_template(db, None, payload.type)
        if not tpl:
            raise HTTPException(status_code=422, detail="template_id обязателен")
    else:
        tpl = _get_template(db, payload.template_id, None)
        if not tpl:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
    client = _get_client(db, payload.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    content = _render(tpl[3], client, payload.data)
    did = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    _insert(db, "documents", {
        "id": did, "client_id": payload.client_id, "template_id": tpl[0],
        "doc_type": payload.type, "title": tpl[2], "content": content,
        "status": "draft", "signed": False,
        "created_at": now, "updated_at": now,
    })
    db.commit()
    return {"document_id": did,
            "pdf_url": f"/api/v1/documents/{did}/download?format=pdf",
            "type": payload.type, "client_id": payload.client_id,
            "template_id": tpl[0], "title": tpl[2], "content": content,
            "message": "Документ создан"}


@router.get("")
def list_documents(client_id: Optional[str] = None, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """E33.3 — список документов (фильтр по клиенту)"""
    q = f"SELECT {_DOC_COLS} FROM documents"
    params = {}
    if client_id:
        q += " WHERE client_id = :cid"
        params["cid"] = client_id
    q += " ORDER BY created_at DESC"
    rows = db.execute(text(q), params).fetchall()
    docs = [_doc_dict(r) for r in rows]
    return {"documents": docs, "total": len(docs)}


@router.get("/templates")
def list_templates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Список доступных шаблонов документов"""
    rows = db.execute(text(
        "SELECT id, code, name FROM document_templates ORDER BY code"
    )).fetchall()
    return {"templates": [{"template_id": r[0], "code": r[1], "name": r[2]}
                          for r in rows]}


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    """E33.4 — документ по ID"""
    r = db.execute(text(
        f"SELECT {_DOC_COLS} FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _doc_dict(r)


@router.post("/{document_id}/sign")
def sign_document(document_id: str, payload: SignRequest,
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33.5/E33.6 — простое подписание документа"""
    r = db.execute(text(
        "SELECT id, signed FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if r[1]:
        raise HTTPException(status_code=400, detail="Документ уже подписан")
    now = datetime.now(timezone.utc)
    db.execute(text(
        "UPDATE documents SET signed = TRUE, signed_at = :t, signature = :s, "
        "status = 'signed', updated_at = :t WHERE id = :id"
    ), {"t": now, "s": payload.signature, "id": document_id})
    db.commit()
    return {"document_id": document_id, "signed": True, "signed_at": str(now),
            "message": "Документ подписан"}


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    """E33.7 — удаление документа"""
    r = db.execute(text(
        "DELETE FROM documents WHERE id = :id RETURNING id"
    ), {"id": document_id}).fetchone()
    db.commit()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return Response(status_code=204)

@router.post("/{document_id}/send-email")
def send_document_email(document_id: str, payload: EmailRequest,
                        db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33.11 — отправка документа на email (эмуляция)"""
    r = db.execute(text(
        "SELECT client_id FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    client = _get_client(db, r[0])
    email = payload.email or (client or {}).get("email") or ""
    return {"document_id": document_id, "email": email,
            "message": "Документ отправлен"}


@router.post("/{document_id}/print")
def print_document(document_id: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """E33.12 — печать документа (эмуляция)"""
    r = db.execute(text(
        "SELECT id FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return {"document_id": document_id,
            "message": "Документ отправлен на печать"}


@router.get("/{document_id}/download")
def download_document(document_id: str, format: str = "pdf",
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33.13/E33.14 — экспорт документа в PDF / DOCX"""
    r = db.execute(text(
        "SELECT title, content FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if format == "pdf":
        return Response(content=_pdf_bytes(r[0], r[1] or ""),
                        media_type="application/pdf")
    if format == "docx":
        return Response(
            content=_docx_bytes(r[0], r[1] or ""),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    raise HTTPException(status_code=400, detail="Неподдерживаемый формат")


@router.post("/{document_id}/sign-ep")
def sign_document_ep(document_id: str, payload: SignEPRequest,
                     db: Session = Depends(get_db), user=Depends(get_current_user)):
    """E33.15 — подписание электронной подписью (CAdES-эмуляция)"""
    r = db.execute(text(
        "SELECT id, signed FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if r[1]:
        raise HTTPException(status_code=400, detail="Документ уже подписан")
    if not payload.certificate:
        raise HTTPException(status_code=400, detail="Сертификат обязателен")
    now = datetime.now(timezone.utc)
    db.execute(text(
        "UPDATE documents SET signed = TRUE, signed_at = :t, signature = :s, "
        "ep_format = 'CAdES', status = 'signed', updated_at = :t WHERE id = :id"
    ), {"t": now, "s": payload.certificate, "id": document_id})
    db.commit()
    return {"document_id": document_id, "signed": True, "signed_at": str(now),
            "signature_valid": True, "signature_format": "CAdES",
            "message": "Документ подписан ЭП"}
