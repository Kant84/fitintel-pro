# -*- coding: utf-8 -*-
"""П1: «Почта разработчика в системе» — обращения в поддержку по email.
IMAP-поллер (celery app.tasks.poll_support_mail) забирает входящие в support_tickets;
ответы уходят через SMTP (notification_settings) с заголовками треда
(In-Reply-To/References), чтобы переписка склеивалась и у клиента, и у нас."""
import json, re, uuid, datetime, imaplib, smtplib, ssl
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr, make_msgid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import engine
from app.api.dependencies import get_current_user

router = APIRouter(tags=["support"])

DEFAULT_SETTINGS = {
    "enabled": False,
    "imap_host": "", "imap_port": 993, "imap_ssl": True,
    "imap_user": "", "imap_password": "",
    "support_email": "support@fixintel.ru",  # официальный канал поддержки
    "from_email": "",         # обратный адрес в ответах (по умолчанию = imap_user)
    "poll_interval": 300,
}


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _ensure():
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS support_tickets("
                       "id TEXT PRIMARY KEY, email TEXT, name TEXT, subject TEXT, "
                       "status TEXT DEFAULT 'new', created_at TEXT, updated_at TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS support_messages("
                       "id TEXT PRIMARY KEY, ticket_id TEXT, direction TEXT, body TEXT, "
                       "created_at TEXT, message_id TEXT, in_reply_to TEXT, headers TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS support_settings("
                       "id INTEGER PRIMARY KEY, config TEXT, updated_at TEXT)"))


def get_settings():
    _ensure()
    with engine.begin() as c:
        row = c.execute(text("SELECT config FROM support_settings WHERE id=1")).fetchone()
    cfg = dict(DEFAULT_SETTINGS)
    if row and row[0]:
        try:
            cfg.update(json.loads(row[0]))
        except Exception:
            pass
    return cfg


def _save_settings(cfg):
    _ensure()
    with engine.begin() as c:
        c.execute(text("INSERT INTO support_settings(id, config, updated_at) "
                       "VALUES(1, :cfg, :t) ON CONFLICT(id) DO UPDATE SET "
                       "config=:cfg, updated_at=:t"),
                  {"cfg": json.dumps(cfg, ensure_ascii=False), "t": _now()})


# ---------- настройки ----------
@router.get("/support/settings")
def support_settings(current=Depends(get_current_user)):
    cfg = get_settings()
    cfg["imap_password"] = "***" if cfg.get("imap_password") else ""
    return cfg


class SettingsIn(BaseModel):
    enabled: Optional[bool] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_ssl: Optional[bool] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    support_email: Optional[str] = None
    from_email: Optional[str] = None
    poll_interval: Optional[int] = None


@router.put("/support/settings")
def support_settings_put(body: SettingsIn, current=Depends(get_current_user)):
    cfg = get_settings()
    data = body.dict(exclude_unset=True)
    if data.get("imap_password") == "***":
        data.pop("imap_password")
    cfg.update(data)
    _save_settings(cfg)
    out = dict(cfg)
    out["imap_password"] = "***" if out.get("imap_password") else ""
    return {"ok": True, "settings": out}


# ---------- тикеты ----------
@router.get("/support/tickets")
def tickets(status: Optional[str] = None, q: Optional[str] = None,
            limit: int = 200, current=Depends(get_current_user)):
    _ensure()
    sql = ("SELECT t.id, t.email, t.name, t.subject, t.status, t.created_at, t.updated_at,"
           " (SELECT body FROM support_messages m WHERE m.ticket_id=t.id "
           "  ORDER BY m.created_at DESC LIMIT 1),"
           " (SELECT COUNT(*) FROM support_messages m WHERE m.ticket_id=t.id) "
           "FROM support_tickets t")
    where, prm = [], {}
    if status:
        where.append("t.status=:s"); prm["s"] = status
    if q:
        where.append("(t.subject ILIKE :q OR t.email ILIKE :q OR t.name ILIKE :q)")
        prm["q"] = "%" + q + "%"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.updated_at DESC LIMIT %d" % int(limit)
    with engine.begin() as c:
        rows = c.execute(text(sql), prm).fetchall()
    return {"items": [{"id": r[0], "email": r[1], "name": r[2], "subject": r[3],
                       "status": r[4], "created_at": r[5], "updated_at": r[6],
                       "last_body": (r[7] or "")[:120], "messages": r[8]} for r in rows]}


@router.get("/support/tickets/{tid}/messages")
def ticket_messages(tid: str, current=Depends(get_current_user)):
    _ensure()
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT id, direction, body, created_at FROM support_messages "
            "WHERE ticket_id=:t ORDER BY created_at"), {"t": tid}).fetchall()
    return {"items": [{"id": r[0], "direction": r[1], "body": r[2], "created_at": r[3]}
                      for r in rows]}


def _smtp_settings():
    """SMTP из notification_settings (там же живёт конфиг чеков на email)."""
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT config FROM notification_settings WHERE id=1")).fetchone()
    cfg = {}
    if row and row[0]:
        try:
            cfg = json.loads(row[0])
        except Exception:
            pass
    return cfg


class ReplyIn(BaseModel):
    text: str


@router.post("/support/tickets/{tid}/reply")
def ticket_reply(tid: str, body: ReplyIn, current=Depends(get_current_user)):
    _ensure()
    scfg = get_settings()
    if not scfg.get("enabled"):
        raise HTTPException(400, "Поддержка по email выключена (вкладка «MAX сообщения → Поддержка», настройки)")
    smtp = _smtp_settings()
    host = smtp.get("smtp_host")
    user = smtp.get("smtp_user")
    pwd = smtp.get("smtp_password")
    if not host or not user or not pwd:
        raise HTTPException(400, "SMTP не настроен (Уведомления → Email: хост/логин/пароль приложения)")
    with engine.begin() as c:
        t = c.execute(text("SELECT id, email, subject FROM support_tickets WHERE id=:t"),
                      {"t": tid}).fetchone()
        if not t:
            raise HTTPException(404, "Обращение не найдено")
        last = c.execute(text(
            "SELECT message_id, headers FROM support_messages WHERE ticket_id=:t "
            "ORDER BY created_at DESC LIMIT 1"), {"t": tid}).fetchone()
    refs = []
    in_reply_to = None
    if last and last[0]:
        try:
            hdrs = json.loads(last[1] or "{}")
            in_reply_to = last[0]
            refs = [last[0]] + (hdrs.get("references") or [])
        except Exception:
            in_reply_to = last[0]
    msg = EmailMessage()
    from_email = scfg.get("from_email") or scfg.get("imap_user") or user
    msg["From"] = from_email
    msg["To"] = t[1]
    subj = t[2] or ""
    msg["Subject"] = subj if subj.lower().startswith("re:") else "Re: " + subj
    msg["Message-ID"] = make_msgid(domain="fitintel-support")
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = " ".join(refs[-10:])
    msg.set_content(body.text)
    port = int(smtp.get("smtp_port") or 465)
    try:
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            s = smtplib.SMTP(host, port, timeout=20)
            s.starttls(context=ssl.create_default_context())
        s.login(user, pwd)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        raise HTTPException(502, "SMTP ошибка: %s" % str(e)[:200])
    now = _now()
    with engine.begin() as c:
        c.execute(text("INSERT INTO support_messages(id, ticket_id, direction, body, "
                       "created_at, message_id, in_reply_to, headers) "
                       "VALUES(:i,:t,'out',:b,:ca,:m,:r,:h)"),
                  {"i": uuid.uuid4().hex, "t": tid, "b": body.text, "ca": now,
                   "m": msg["Message-ID"], "r": in_reply_to,
                   "h": json.dumps({"references": refs})})
        c.execute(text("UPDATE support_tickets SET status='in_progress', updated_at=:u "
                       "WHERE id=:t"), {"u": now, "t": tid})
    return {"ok": True, "sent": True}


class StatusIn(BaseModel):
    status: str  # new | in_progress | done


@router.put("/support/tickets/{tid}/status")
def ticket_status(tid: str, body: StatusIn, current=Depends(get_current_user)):
    if body.status not in ("new", "in_progress", "done"):
        raise HTTPException(400, "status: new | in_progress | done")
    _ensure()
    with engine.begin() as c:
        r = c.execute(text("UPDATE support_tickets SET status=:s, updated_at=:u WHERE id=:t"),
                      {"s": body.status, "u": _now(), "t": tid})
    if r.rowcount == 0:
        raise HTTPException(404, "Обращение не найдено")
    return {"ok": True}


# ---------- IMAP-поллер ----------
def _decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    out = ""
    for txt, enc in parts:
        if isinstance(txt, bytes):
            out += txt.decode(enc or "utf-8", errors="replace")
        else:
            out += txt
    return out


def _msg_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    pass
                if body:
                    break
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace")
                        body = re.sub(r"<[^>]+>", " ", html)
                        body = re.sub(r"\s+", " ", body).strip()
                    except Exception:
                        pass
                    if body:
                        break
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload() or "")
    return (body or "")[:20000]


def poll_once():
    """Один проход IMAP: непрочитанные -> тикеты/сообщения. Вызывается из celery."""
    _ensure()
    cfg = get_settings()
    if not cfg.get("enabled") or not cfg.get("imap_host") or not cfg.get("imap_user"):
        return {"ok": False, "error": "not_configured"}
    imported = tickets_new = errors = 0
    try:
        if cfg.get("imap_ssl", True):
            conn = imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg.get("imap_port") or 993))
        else:
            conn = imaplib.IMAP4(cfg["imap_host"], int(cfg.get("imap_port") or 143))
        conn.login(cfg["imap_user"], cfg.get("imap_password") or "")
        conn.select("INBOX")
        typ, data = conn.search(None, "UNSEEN")
        ids = (data[0] or b"").split() if typ == "OK" else []
        for num in ids[-50:]:
            try:
                typ, msg_data = conn.fetch(num, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                import email as _email
                msg = _email.message_from_bytes(msg_data[0][1])
                mid = (msg.get("Message-ID") or "").strip() or make_msgid()
                in_reply = (msg.get("In-Reply-To") or "").strip()
                refs = (msg.get("References") or "").split()
                frm = parseaddr(_decode_str(msg.get("From") or ""))
                name, from_email = frm[0], frm[1]
                subject = _decode_str(msg.get("Subject") or "(без темы)")
                body = _msg_body(msg)
                if not from_email:
                    continue
                now = _now()
                with engine.begin() as c:
                    tid = None
                    for ref in [in_reply] + refs:
                        if not ref:
                            continue
                        row = c.execute(text(
                            "SELECT ticket_id FROM support_messages WHERE message_id=:m"),
                            {"m": ref}).fetchone()
                        if row:
                            tid = row[0]
                            break
                    if not tid:
                        tid = "st-" + uuid.uuid4().hex[:12]
                        c.execute(text("INSERT INTO support_tickets(id, email, name, subject, "
                                       "status, created_at, updated_at) "
                                       "VALUES(:i,:e,:n,:s,'new',:ca,:ca)"),
                                  {"i": tid, "e": from_email, "n": name, "s": subject,
                                   "ca": now})
                        tickets_new += 1
                    c.execute(text("INSERT INTO support_messages(id, ticket_id, direction, body, "
                                   "created_at, message_id, in_reply_to, headers) "
                                   "VALUES(:i,:t,'in',:b,:ca,:m,:r,:h)"),
                              {"i": uuid.uuid4().hex, "t": tid, "b": body, "ca": now,
                               "m": mid, "r": in_reply,
                               "h": json.dumps({"references": refs})})
                    c.execute(text("UPDATE support_tickets SET updated_at=:u WHERE id=:t"),
                              {"u": now, "t": tid})
                imported += 1
                conn.store(num, "+FLAGS", "\\Seen")
            except Exception as e:
                errors += 1
                print("[support] msg parse:", str(e)[:120])
        conn.logout()
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    return {"ok": True, "imported": imported, "new_tickets": tickets_new, "errors": errors}
# ---------- ручной опрос (кнопка в desktop) ----------
@router.post("/support/poll-now")
def poll_now(current=Depends(get_current_user)):
    """Немедленный проход IMAP-поллера (без ожидания beat)."""
    return poll_once()


# ---------- П1 (модель «клуб -> разработчик»): отправка обращений ----------
SUPPORT_TO = "support@fixintel.ru"  # ящик техподдержки; зашит на сервере, из desktop не меняется


def _ensure_outbox():
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS support_outbox("
                       "id TEXT PRIMARY KEY, subject TEXT, body TEXT, "
                       "status TEXT, error TEXT, created_at TEXT)"))


class SendIn(BaseModel):
    subject: str
    text: str


@router.post("/support/send")
def support_send(body: SendIn, current=Depends(get_current_user)):
    _ensure_outbox()
    if not body.text.strip():
        raise HTTPException(400, "Текст обращения пуст")
    cfg = get_settings()
    host = cfg.get("smtp_host") or cfg.get("imap_host")
    port = int(cfg.get("smtp_port") or 465)
    user = cfg.get("smtp_user") or cfg.get("imap_user")
    pwd = cfg.get("smtp_password") or cfg.get("imap_password")
    if not host or not user or not pwd:
        raise HTTPException(400, "Не настроен почтовый ящик клуба: сервер / ящик / пароль")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = SUPPORT_TO
    msg["Subject"] = "[FitIntel Pro] " + (body.subject.strip() or "Обращение в поддержку")
    msg["Message-ID"] = make_msgid(domain="fitintel-support")
    msg.set_content(body.text)
    status, error = "sent", None
    try:
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=25)
        else:
            s = smtplib.SMTP(host, port, timeout=25)
            s.starttls(context=ssl.create_default_context())
        s.login(user, pwd)
        s.send_message(msg)
        s.quit()
    except Exception as e:
        status, error = "error", str(e)[:300]
    with engine.begin() as c:
        c.execute(text("INSERT INTO support_outbox(id, subject, body, status, error, created_at) "
                       "VALUES(:i,:s,:b,:st,:e,:ca)"),
                  {"i": uuid.uuid4().hex, "s": body.subject, "b": body.text,
                   "st": status, "e": error, "ca": _now()})
    if status != "sent":
        raise HTTPException(502, "Не удалось отправить: %s" % error)
    return {"ok": True, "to": SUPPORT_TO}


@router.get("/support/outbox")
def support_outbox(limit: int = 100, current=Depends(get_current_user)):
    _ensure_outbox()
    with engine.begin() as c:
        rows = c.execute(text("SELECT id, subject, status, error, created_at "
                              "FROM support_outbox ORDER BY created_at DESC LIMIT %d" % int(limit))).fetchall()
    return {"items": [{"id": r[0], "subject": r[1], "status": r[2],
                       "error": r[3], "created_at": r[4]} for r in rows]}


@router.get("/support/outbox/{oid}")
def support_outbox_item(oid: str, current=Depends(get_current_user)):
    _ensure_outbox()
    with engine.begin() as c:
        r = c.execute(text("SELECT subject, body, status, error, created_at "
                           "FROM support_outbox WHERE id=:i"), {"i": oid}).fetchone()
    if not r:
        raise HTTPException(404, "Не найдено")
    return {"subject": r[0], "body": r[1], "status": r[2], "error": r[3], "created_at": r[4]}
