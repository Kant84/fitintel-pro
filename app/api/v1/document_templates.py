"""Document templates CRUD (admin-created reusable templates)."""
import re as _re, logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()

# auth опционально: если get_current_user нет - работаем без него
try:
    from app.api.v1.auth import get_current_user as _gcu
    AUTH_DEP = Depends(_gcu)
except Exception:
    def _noop():
        return None
    AUTH_DEP = Depends(_noop)

_engine = None
def _eng():
    global _engine
    if _engine is None:
        for mod in ("app.db.session", "app.core.database", "app.database"):
            try:
                m = __import__(mod, fromlist=["engine"])
                _engine = getattr(m, "engine")
                break
            except Exception:
                continue
    if _engine is None:
        raise HTTPException(500, "DB engine not found")
    return _engine

def _ensure():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS document_templates (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE,
            name VARCHAR(255) NOT NULL,
            doc_type VARCHAR(64) DEFAULT 'contract',
            content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW())"""))
        for _stmt in (
            "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS doc_type VARCHAR(64) DEFAULT 'contract'",
            "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS content TEXT DEFAULT ''",
            "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS code VARCHAR(64)",
            "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
        ):
            c.execute(text(_stmt))
        c.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_doc_templates_code ON document_templates(code)"))
    for _stmt in (
        "CREATE SEQUENCE IF NOT EXISTS document_templates_id_seq",
        "ALTER TABLE document_templates ALTER COLUMN id SET DEFAULT gen_random_uuid()",
        "ALTER TABLE document_templates ALTER COLUMN id SET DEFAULT nextval('document_templates_id_seq')",
    ):
        try:
            with _eng().begin() as _m:
                _m.execute(text(_stmt))
        except Exception:
            pass


    try:
        with _eng().begin() as s2:
            s2.execute(text("INSERT INTO document_templates (code, name, doc_type, content) SELECT 'contract_std', 'Договор (стандартный)', 'contract', 'ДОГОВОР' WHERE NOT EXISTS (SELECT 1 FROM document_templates WHERE code='contract_std')"))
    except Exception as e:
        logger.warning("seed skip: %s", e)

class TemplateIn(BaseModel):
    name: str
    doc_type: str = "contract"
    content: str = ""

@router.get("")
@router.get("/")
def list_templates(user=AUTH_DEP):
    _ensure()
    with _eng().connect() as c:
        rows = c.execute(text("SELECT id, code, name, doc_type, content, created_at FROM document_templates ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]

@router.post("")
@router.post("/")
def create_template(body: TemplateIn, user=AUTH_DEP):
    import traceback
    try:
        return _create_inner(body)
    except Exception:
        return {"ok": False, "error": traceback.format_exc()}

def _create_inner(body):
    _ensure()
    _slug = _re.sub(r"[^a-z0-9]+", "_", (body.name or "tpl").lower()).strip("_")[:40]
    code = _slug or "tpl"
    with _eng().begin() as _chk:
        if _chk.execute(text("SELECT 1 FROM document_templates WHERE code=:c"), {"c": code}).fetchone():
            import uuid as _uuid
            code = (_slug or "tpl") + "_" + _uuid.uuid4().hex[:8]
    with _eng().begin() as c:
        r = c.execute(text("UPDATE document_templates SET name=:n, doc_type=:t, content=:ct WHERE code=:c"),
                      {"c": code, "n": body.name, "t": body.doc_type, "ct": body.content})
        if r.rowcount == 0:
            c.execute(text("INSERT INTO document_templates (code, name, doc_type, content) VALUES (:c,:n,:t,:ct)"),
                      {"c": code, "n": body.name, "t": body.doc_type, "ct": body.content})
    return {"ok": True, "code": code}

@router.put("/{tpl_id}")
def update_template(tpl_id: str, body: TemplateIn, user=AUTH_DEP):
    _ensure()
    rc = 0
    with _eng().begin() as c:
        r = c.execute(text(
            "UPDATE document_templates SET name=:n, doc_type=:t, content=:ct WHERE id=:i"),
            {"n": body.name, "t": body.doc_type, "ct": body.content, "i": tpl_id})
        rc = r.rowcount
    return {"ok": True, "updated": rc}


@router.post("/upload")
async def upload_template(file: UploadFile = File(...), name: str = Form(None),
                          doc_type: str = Form("other"), user=AUTH_DEP):
    """Загрузка шаблона из файла (.docx — текст извлекается, .txt — как есть)."""
    _ensure()
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(400, "Файл больше 2 МБ")
    fname = (file.filename or "").lower()
    if fname.endswith(".docx"):
        import zipfile, io as _io
        try:
            z = zipfile.ZipFile(_io.BytesIO(raw))
            xml = z.read("word/document.xml").decode("utf-8", "replace")
            xml = xml.replace("</w:p>", "\n")
            content = _re.sub(r"<[^>]+>", "", xml)
        except Exception as e:
            raise HTTPException(400, "Не удалось прочитать .docx: %s" % e)
    elif fname.endswith(".txt"):
        content = raw.decode("utf-8", "replace")
    else:
        raise HTTPException(400, "Поддерживаются .docx и .txt. Старый .doc — сохраните как .docx в Word.")
    body = TemplateIn(name=(name or file.filename or "Шаблон"), doc_type=doc_type, content=content.strip())
    return _create_inner(body)

@router.delete("/{tpl_id}")
def delete_template(tpl_id: str, user=AUTH_DEP):
    _ensure()
    with _eng().begin() as c:
        c.execute(text("DELETE FROM document_templates WHERE id=:i"), {"i": tpl_id})
    return {"ok": True}
