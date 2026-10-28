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
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as _xesc

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.services.audit_service import AuditService
from app.services.document_archive import DocumentArchive

router = APIRouter(prefix="/documents", tags=["Documents E33"])
READ_DEP = Depends(require_permission("documents.read"))
CREATE_DEP = Depends(require_permission("documents.create"))
DELETE_DEP = Depends(require_permission("documents.delete"))


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


_PDF_FONT = "FitIntelDejaVuSans"
_PDF_FONT_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "fonts" / "DejaVuSans.ttf"
)
if not _PDF_FONT_PATH.is_file():
    # Локальная разработка: в production Dockerfile копирует этот же шрифт
    # в /app/static/fonts/DejaVuSans.ttf.
    _PDF_FONT_PATH = (
        Path(__file__).resolve().parents[3]
        / "fitintel-desktop" / "assets" / "DejaVuSans.ttf"
    )


def _pdf_bytes(title: str, content: str) -> bytes:
    if _PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        if not _PDF_FONT_PATH.is_file():
            raise RuntimeError("Unicode PDF font is not installed")
        pdfmetrics.registerFont(TTFont(_PDF_FONT, str(_PDF_FONT_PATH)))

    body_style = ParagraphStyle(
        "DocumentBody", fontName=_PDF_FONT, fontSize=11, leading=16,
        splitLongWords=True,
    )
    title_style = ParagraphStyle(
        "DocumentTitle", parent=body_style, fontSize=15, leading=20,
        spaceAfter=8,
    )
    story = [Paragraph(_xesc(title or "Документ"), title_style), Spacer(1, 2 * mm)]
    story.extend(
        Paragraph(_xesc(line) if line else "&#160;", body_style)
        for line in (content or "").split("\n")
    )
    buf = io.BytesIO()
    document = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    document.build(story)
    return buf.getvalue()


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


_DOC_COLS = ("id, client_id, template_id, doc_type, title, pdf_data, status, "
             "signed_at, created_at")

def _doc_dict(r):
    return {"document_id": r[0], "client_id": r[1], "template_id": r[2],
            "type": r[3], "title": r[4], "content": r[5], "status": r[6],
            "signed": r[6] == "signed",
            "signed_at": str(r[7]) if r[7] else None,
            "pdf_url": f"/api/v1/documents/{r[0]}/download?format=pdf",
            "created_at": str(r[8]) if r[8] else None}

@router.post("", status_code=201)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db),
                    user=CREATE_DEP):
    """Создаёт документ и первую неизменяемую серверную файловую версию."""
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
    pdf = _pdf_bytes(tpl[2], content)
    docx = _docx_bytes(tpl[2], content)
    archive = DocumentArchive()
    files = archive.write_version(did, 1, pdf, docx)
    try:
        _insert(db, "documents", {
            "id": did, "client_id": payload.client_id, "template_id": tpl[0],
            "doc_type": payload.type, "title": tpl[2],
            "filename": f"{tpl[1] or payload.type}.pdf",
            "content_type": "application/pdf", "file_size": len(pdf),
            "pdf_data": content, "generated_by": str(user.id),
            "status": "draft", "created_at": now, "updated_at": now,
        })
        _insert(db, "document_versions", {
            "id": str(uuid.uuid4()), "document_id": did, "version": 1,
            **files, "created_by": str(user.id), "created_at": now,
        })
        db.commit()
    except Exception:
        db.rollback()
        archive.delete([files["pdf_path"], files["docx_path"]])
        raise

    AuditService(db).created(
        actor_user_id=user.id, entity_type="document", entity_id=did,
        message="Документ и первая архивная версия созданы",
        after_data={"version": 1, **files},
    )
    return {"document_id": did,
            "pdf_url": f"/api/v1/documents/{did}/download?format=pdf",
            "type": payload.type, "client_id": payload.client_id,
            "template_id": tpl[0], "title": tpl[2], "content": content,
            "archive": {"version": 1, **files},
            "message": "Документ создан"}


@router.get("")
def list_documents(client_id: Optional[str] = None, db: Session = Depends(get_db),
                   user=READ_DEP):
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
def list_templates(db: Session = Depends(get_db), user=READ_DEP):
    """Список доступных шаблонов документов"""
    rows = db.execute(text(
        "SELECT id, code, name FROM document_templates ORDER BY code"
    )).fetchall()
    return {"templates": [{"template_id": r[0], "code": r[1], "name": r[2]}
                          for r in rows]}


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db),
                 user=READ_DEP):
    """E33.4 — документ по ID"""
    r = db.execute(text(
        f"SELECT {_DOC_COLS} FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _doc_dict(r)


@router.get("/{document_id}/versions")
def list_document_versions(document_id: str, db: Session = Depends(get_db),
                           user=READ_DEP):
    """Публичные метаданные версий без раскрытия серверных путей."""
    exists = db.execute(text(
        "SELECT id FROM documents WHERE id = :id"
    ), {"id": document_id}).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Документ не найден")
    rows = db.execute(text(
        "SELECT version, pdf_sha256, pdf_size, docx_sha256, docx_size, "
        "created_by, created_at FROM document_versions "
        "WHERE document_id = :id ORDER BY version DESC"
    ), {"id": document_id}).fetchall()
    return {"versions": [{
        "version": row[0], "pdf_sha256": row[1], "pdf_size": row[2],
        "docx_sha256": row[3], "docx_size": row[4],
        "created_by": str(row[5]) if row[5] else None,
        "created_at": str(row[6]) if row[6] else None,
    } for row in rows]}


@router.post("/{document_id}/sign")
def sign_document(document_id: str, payload: SignRequest,
                  db: Session = Depends(get_db), user=CREATE_DEP):
    """E33.5/E33.6 — простое подписание документа"""
    _cols = {row[0] for row in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='documents'")).fetchall()}
    _sel = "id, signed" if "signed" in _cols else "id, status"
    r = db.execute(text(
        "SELECT %s FROM documents WHERE id = :id" % _sel
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if r[1] and (r[1] is True or r[1] == "signed"):
        raise HTTPException(status_code=400, detail="Документ уже подписан")
    now = datetime.now(timezone.utc)
    _sets = []
    if "status" in _cols:
        _sets.append("status = 'signed'")
    if "signed" in _cols:
        _sets.append("signed = TRUE")
    if "signed_at" in _cols:
        _sets.append("signed_at = :t")
    if "signed_by" in _cols:
        _sets.append("signed_by = :actor")
    if "updated_at" in _cols:
        _sets.append("updated_at = :t")
    if not _sets:
        raise HTTPException(status_code=500, detail="documents: нет колонок для подписания")
    db.execute(text(
        "UPDATE documents SET %s WHERE id = :id" % ", ".join(_sets)
    ), {"t": now, "id": document_id, "actor": str(user.id)})
    db.commit()
    AuditService(db).log(
        action="document.sign", status="success", actor_user_id=user.id,
        entity_type="document", entity_id=document_id,
        message="Документ подписан; архивная версия не изменена",
        after_data={"signed_at": now},
    )
    return {"document_id": document_id, "signed": True, "signed_at": str(now),
            "message": "Документ подписан"}


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db),
                    user=DELETE_DEP):
    """Удаляет документ и его архивные файлы; права выдаёт только RBAC."""
    paths = db.execute(text(
        "SELECT pdf_path, docx_path FROM document_versions WHERE document_id = :id"
    ), {"id": document_id}).fetchall()
    r = db.execute(text(
        "DELETE FROM documents WHERE id = :id RETURNING id"
    ), {"id": document_id}).fetchone()
    db.commit()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")
    archive = DocumentArchive()
    archive.delete([str(path) for row in paths for path in row])
    AuditService(db).deleted(
        actor_user_id=user.id, entity_type="document", entity_id=document_id,
        message="Документ и его архивные файлы удалены",
    )
    return Response(status_code=204)

@router.post("/{document_id}/send-email")
def send_document_email(document_id: str, payload: EmailRequest,
                        db: Session = Depends(get_db), user=CREATE_DEP):
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
                   user=CREATE_DEP):
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
                      db: Session = Depends(get_db), user=READ_DEP):
    """Скачивает архивную версию; legacy-документы читает по-старому."""
    if format not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат")
    _cols = {row[0] for row in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='documents'")).fetchall()}
    _c_title = next((c for c in ("title", "name") if c in _cols), None)
    _c_body = next(
        (c for c in ("content", "body", "text", "html", "pdf_data") if c in _cols),
        None,
    )
    if not _c_title:
        raise HTTPException(status_code=500, detail="documents: нет колонки title/name")
    r = db.execute(text(
        "SELECT %s, %s FROM documents WHERE id = :id" % (_c_title, _c_body or _c_title)
    ), {"id": document_id}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Документ не найден")

    version = db.execute(text(
        "SELECT version, pdf_path, pdf_sha256, docx_path, docx_sha256 "
        "FROM document_versions WHERE document_id = :id "
        "ORDER BY version DESC LIMIT 1"
    ), {"id": document_id}).mappings().fetchone()
    if version:
        try:
            content = DocumentArchive().read(
                version[f"{format}_path"], version[f"{format}_sha256"]
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Архивный файл не найден")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        sha256 = version[f"{format}_sha256"]
        version_number = version["version"]
    else:
        # Только для документов, созданных до появления архива. Если строка
        # версии существует, потерянный/изменённый файл не подменяется генерацией.
        content = (_pdf_bytes if format == "pdf" else _docx_bytes)(r[0], r[1] or "")
        sha256 = None
        version_number = None

    AuditService(db).log(
        action="document.download", status="success", actor_user_id=user.id,
        entity_type="document", entity_id=document_id,
        message="Выгружена копия документа",
        after_data={"format": format, "version": version_number,
                    "legacy": version is None, "sha256": sha256},
    )
    media_type = (
        "application/pdf" if format == "pdf" else
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    headers = {"X-Document-Version": str(version_number or "legacy")}
    if sha256:
        headers["X-SHA256"] = sha256
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/{document_id}/sign-ep")
def sign_document_ep(document_id: str, payload: SignEPRequest,
                     db: Session = Depends(get_db), user=CREATE_DEP):
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
    _cols2 = {row[0] for row in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='documents'")).fetchall()}
    _sets2 = []
    if "signed" in _cols2:
        _sets2.append("signed = TRUE")
    if "status" in _cols2:
        _sets2.append("status = 'signed'")
    if "signed_at" in _cols2:
        _sets2.append("signed_at = :t")
    if "signed_by" in _cols2:
        _sets2.append("signed_by = :actor")
    if "updated_at" in _cols2:
        _sets2.append("updated_at = :t")
    if "signature" in _cols2:
        _sets2.append("signature = :s")
    if "ep_format" in _cols2:
        _sets2.append("ep_format = 'CAdES'")
    if not _sets2:
        raise HTTPException(status_code=500, detail="documents: нет колонок для подписания")
    db.execute(text(
        "UPDATE documents SET %s WHERE id = :id" % ", ".join(_sets2)
    ), {"t": now, "s": payload.certificate, "id": document_id,
        "actor": str(user.id)})
    db.commit()
    AuditService(db).log(
        action="document.sign_ep", status="success", actor_user_id=user.id,
        entity_type="document", entity_id=document_id,
        message="Документ подписан ЭП; архивная версия не изменена",
        after_data={"signed_at": now, "signature_format": "CAdES"},
    )
    return {"document_id": document_id, "signed": True, "signed_at": str(now),
            "signature_valid": True, "signature_format": "CAdES",
            "message": "Документ подписан ЭП"}
