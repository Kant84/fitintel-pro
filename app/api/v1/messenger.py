# -*- coding: utf-8 -*-
"""E56/E57/E58: MAX-мессенджер — чаты, рассылки, привязки, настройки оповещений."""
import json
import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

engine = None
for mod in ("app.db.session", "app.core.database", "app.database"):
    try:
        m = __import__(mod, fromlist=["engine"])
        engine = m.engine
        break
    except Exception:
        continue
if engine is None:
    raise RuntimeError("messenger: engine not found")

router = APIRouter(tags=["messenger"])
MAX_API = "https://platform-api.max.ru"
MAX_API_LP = "https://platform-api2.max.ru"

DEFAULT_SETTINGS = {
    "enabled": True,
    "channel_max": True,
    "send_time": "10:00",
    "auto_dispatch": True,
    "expiry_enabled": True,
    "expiry_days": 3,
    "expiry_template": "Ваш абонемент заканчивается через {days} дн. ({date}). Продлите на ресепшене или в приложении!",
    "inactive_enabled": True,
    "inactive_days": 14,
    "inactive_template": "Мы по вам скучаем! Вас не было {days} дней — загляните на тренировку на этой неделе 💪",
    "birthday_enabled": False,
    "birthday_template": "С днём рождения! Дарим скидку 10% на продление абонемента 🎉",
}


def _ensure():
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS messenger_chats("
                       "chat_id TEXT PRIMARY KEY, client_name TEXT, source TEXT, "
                       "last_message TEXT, updated_at TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS messenger_messages("
                       "id TEXT PRIMARY KEY, chat_id TEXT, direction TEXT, "
                       "body TEXT, created_at TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS messenger_bindings("
                       "client_id TEXT PRIMARY KEY, max_user_id TEXT, "
                       "client_name TEXT, role TEXT, bound_at TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS messenger_notifications("
                       "id TEXT PRIMARY KEY, target_id TEXT, target_name TEXT, "
                       "kind TEXT, body TEXT, status TEXT, detail TEXT, "
                       "created_at TEXT, sent_at TEXT)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS notification_settings("
                       "id INTEGER PRIMARY KEY, config TEXT, updated_at TEXT)"))


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _max_token():
    _ensure()
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT config FROM integration_settings "
            "WHERE service='max_messenger'")).fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0]).get("bot_token")
        except Exception:
            return None
    return None


def _send_max(max_user_id, body):
    tok = _max_token()
    if not tok:
        return False, "no_token"
    try:
        import requests
        r = requests.post(MAX_API + "/messages",
                          params={"user_id": int(max_user_id)},
                          json={"text": body},
                          headers={"Authorization": tok}, timeout=10)
        return r.status_code == 200, "HTTP %s" % r.status_code
    except Exception as e:
        return False, str(e)


def _binding(c, client_id):
    return c.execute(text(
        "SELECT max_user_id, client_name FROM messenger_bindings "
        "WHERE client_id=:c"), {"c": str(client_id)}).fetchone()


def _mk_note(c, target_id, name, kind, body, status="pending"):
    nid = uuid.uuid4().hex
    c.execute(text("INSERT INTO messenger_notifications("
                   "id, target_id, target_name, kind, body, status, detail, "
                   "created_at, sent_at) VALUES(:i,:t,:n,:k,:b,:s,'',:ca,NULL)"),
              {"i": nid, "t": str(target_id), "n": name, "k": kind, "b": body,
               "s": status, "ca": _now()})
    return nid


def _dispatch_pending():
    sent = failed = 0
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT id, target_id, body FROM messenger_notifications "
            "WHERE status='pending'")).fetchall()
        for nid, tid, body in rows:
            b = _binding(c, tid)
            if not b or not b[0]:
                c.execute(text("UPDATE messenger_notifications SET "
                               "status='no_binding', detail='нет привязки MAX' "
                               "WHERE id=:i"), {"i": nid})
                continue
            ok, detail = _send_max(b[0], body)
            c.execute(text("UPDATE messenger_notifications SET status=:s, "
                           "detail=:d, sent_at=:t WHERE id=:i"),
                      {"s": "sent" if ok else "failed", "d": detail,
                       "t": _now(), "i": nid})
            sent += 1 if ok else 0
            failed += 0 if ok else 1
    return sent, failed


# ---------- настройки оповещений ----------
def _get_settings():
    _ensure()
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT config FROM notification_settings WHERE id=1")).fetchone()
    cfg = dict(DEFAULT_SETTINGS)
    if row and row[0]:
        try:
            cfg.update(json.loads(row[0]))
        except Exception:
            pass
    return cfg


@router.get("/messenger/settings")
def get_settings():
    return _get_settings()


@router.put("/messenger/settings")
def put_settings(body: dict):
    cfg = _get_settings()
    cfg.update(body)
    with engine.begin() as c:
        c.execute(text("INSERT INTO notification_settings(id, config, updated_at) "
                       "VALUES(1, :cfg, :t) ON CONFLICT(id) DO UPDATE SET "
                       "config=:cfg, updated_at=:t"),
                  {"cfg": json.dumps(cfg, ensure_ascii=False), "t": _now()})
    return {"ok": True, "settings": cfg}


# ---------- чаты ----------
@router.get("/messenger/chats")
def chats():
    _ensure()
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT chat_id, client_name, source, last_message, updated_at "
            "FROM messenger_chats ORDER BY updated_at DESC")).fetchall()
    return {"items": [{"chat_id": r[0], "client_name": r[1], "source": r[2],
                       "last_message": r[3], "updated_at": r[4]} for r in rows]}


@router.get("/messenger/chats/{chat_id}/messages")
def messages(chat_id: str):
    _ensure()
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT id, direction, body, created_at FROM messenger_messages "
            "WHERE chat_id=:c ORDER BY created_at"), {"c": chat_id}).fetchall()
    return {"items": [{"id": r[0], "direction": r[1], "body": r[2],
                       "created_at": r[3]} for r in rows]}


class MsgIn(BaseModel):
    text: str


@router.post("/messenger/chats/{chat_id}/send")
def send(chat_id: str, body: MsgIn):
    _ensure()
    now = _now()
    with engine.begin() as c:
        c.execute(text("INSERT INTO messenger_messages(id, chat_id, direction, "
                       "body, created_at) VALUES(:i,:c,'out',:b,:t)"),
                  {"i": uuid.uuid4().hex, "c": chat_id, "b": body.text, "t": now})
        c.execute(text("UPDATE messenger_chats SET last_message=:b, "
                       "updated_at=:t WHERE chat_id=:c"),
                  {"b": body.text, "t": now, "c": chat_id})
    sent = False
    tok = _max_token()
    if tok and str(chat_id).lstrip("-").isdigit():
        try:
            import requests
            r = requests.post(MAX_API + "/messages",
                              params={"chat_id": int(chat_id)},
                              json={"text": body.text},
                              headers={"Authorization": tok}, timeout=10)
            sent = r.status_code == 200
        except Exception:
            pass
    return {"ok": True, "sent_to_max": sent}


@router.post("/messenger/max/sync")
def sync():
    _ensure()
    tok = _max_token()
    if not tok:
        raise HTTPException(400, "MAX не настроен: задайте bot_token "
                                 "на вкладке «Интеграции» (max_messenger)")
    try:
        import requests
        r = requests.get(MAX_API_LP + "/updates",
                         params={"types": "message_created", "timeout": 5},
                         headers={"Authorization": tok}, timeout=15)
        if r.status_code != 200:
            raise HTTPException(502, "MAX API HTTP %s: %s" % (r.status_code, r.text[:200]))
        updates = r.json().get("updates", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, "MAX API: %s" % e)
    n = 0
    with engine.begin() as c:
        for u in updates:
            msg = u.get("message") or {}
            txt = ((msg.get("body") or {}).get("text")) or ""
            sender = ((msg.get("sender") or {}).get("name")) or "Клиент"
            chat = (msg.get("recipient") or {}).get("chat_id")
            if not chat or not txt:
                continue
            cid = str(chat)
            now = _now()
            if not c.execute(text("SELECT chat_id FROM messenger_chats "
                                  "WHERE chat_id=:c"), {"c": cid}).fetchone():
                c.execute(text("INSERT INTO messenger_chats(chat_id, client_name, "
                               "source, last_message, updated_at) "
                               "VALUES(:c,:n,'max',:l,:t)"),
                          {"c": cid, "n": sender, "l": txt, "t": now})
            else:
                c.execute(text("UPDATE messenger_chats SET last_message=:l, "
                               "updated_at=:t WHERE chat_id=:c"),
                          {"l": txt, "t": now, "c": cid})
            c.execute(text("INSERT INTO messenger_messages(id, chat_id, direction, "
                           "body, created_at) VALUES(:i,:c,'in',:b,:t)"),
                      {"i": uuid.uuid4().hex, "c": cid, "b": txt, "t": now})
            n += 1
    return {"ok": True, "imported": n}


# ---------- привязки ----------
class BindIn(BaseModel):
    client_id: str
    max_user_id: str
    client_name: Optional[str] = None
    role: str = "client"


@router.get("/messenger/bindings")
def bindings():
    _ensure()
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT client_id, max_user_id, client_name, role, bound_at "
            "FROM messenger_bindings ORDER BY bound_at DESC")).fetchall()
    return {"items": [{"client_id": r[0], "max_user_id": r[1],
                       "client_name": r[2], "role": r[3],
                       "bound_at": r[4]} for r in rows]}


@router.post("/messenger/bindings")
def bind(body: BindIn):
    _ensure()
    with engine.begin() as c:
        c.execute(text("INSERT INTO messenger_bindings(client_id, max_user_id, "
                       "client_name, role, bound_at) VALUES(:c,:m,:n,:r,:t) "
                       "ON CONFLICT(client_id) DO UPDATE SET max_user_id=:m, "
                       "client_name=:n, role=:r, bound_at=:t"),
                  {"c": body.client_id, "m": body.max_user_id,
                   "n": body.client_name or "", "r": body.role, "t": _now()})
    return {"ok": True}


# ---------- уведомления ----------
class NotifyIn(BaseModel):
    client_id: str
    text: str
    kind: str = "info"


@router.post("/messenger/notify")
def notify(body: NotifyIn):
    _ensure()
    with engine.begin() as c:
        b = _binding(c, body.client_id)
        name = b[1] if b else body.client_id
        _mk_note(c, body.client_id, name, body.kind, body.text)
    sent, failed = _dispatch_pending()
    return {"ok": True, "sent": sent, "failed": failed}


class BroadcastIn(BaseModel):
    audience: str = "clients"
    text: str
    kind: str = "promo"
    client_ids: Optional[List[str]] = None


@router.post("/messenger/broadcast")
def broadcast(body: BroadcastIn):
    _ensure()
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT client_id, max_user_id, client_name, role "
            "FROM messenger_bindings")).fetchall()
        targets = []
        for cid, _m, name, role in rows:
            if body.client_ids and cid not in body.client_ids:
                continue
            if body.audience == "clients" and role != "client":
                continue
            if body.audience == "trainers" and role != "trainer":
                continue
            targets.append((cid, name))
        for cid, name in targets:
            _mk_note(c, cid, name, body.kind, body.text)
    sent, failed = _dispatch_pending()
    return {"ok": True, "queued": len(targets), "sent": sent, "failed": failed}


@router.get("/messenger/notifications")
def notifications(status: Optional[str] = None, limit: int = 200):
    _ensure()
    q = ("SELECT id, target_name, kind, body, status, detail, created_at, sent_at "
         "FROM messenger_notifications")
    prm = {}
    if status:
        q += " WHERE status=:s"
        prm["s"] = status
    q += " ORDER BY created_at DESC LIMIT %d" % int(limit)
    with engine.begin() as c:
        rows = c.execute(text(q), prm).fetchall()
    return {"items": [{"id": r[0], "target_name": r[1], "kind": r[2],
                       "body": r[3], "status": r[4], "detail": r[5],
                       "created_at": r[6], "sent_at": r[7]} for r in rows]}


@router.post("/messenger/notifications/dispatch")
def dispatch():
    sent, failed = _dispatch_pending()
    return {"ok": True, "sent": sent, "failed": failed}


# ---------- автонапоминания (по настройкам) ----------
def _fmt(tpl, **kw):
    out = tpl
    for k, v in kw.items():
        out = out.replace("{%s}" % k, str(v))
    return out


@router.post("/messenger/reminders/run")
def reminders_run():
    _ensure()
    cfg = _get_settings()
    if not cfg.get("enabled"):
        return {"ok": True, "created": 0, "notes": ["оповещения выключены в настройках"]}
    made = 0
    notes = []
    today = datetime.date.today()

    def _already(c, tid, body):
        return c.execute(text(
            "SELECT id FROM messenger_notifications WHERE target_id=:t AND "
            "body=:b AND created_at LIKE :d"),
            {"t": str(tid), "b": body, "d": str(today) + "%"}).fetchone()

    if cfg.get("expiry_enabled"):
        try:
            with engine.begin() as c:
                rows = c.execute(text(
                    "SELECT client_id, end_date FROM subscriptions")).fetchall()
                for cid, end in rows:
                    try:
                        d = datetime.date.fromisoformat(str(end)[:10])
                    except Exception:
                        continue
                    days = (d - today).days
                    if 0 <= days <= int(cfg.get("expiry_days", 3)):
                        body = _fmt(cfg["expiry_template"], days=days, date=d)
                        if not _already(c, cid, body):
                            _mk_note(c, cid, str(cid), "reminder", body)
                            made += 1
        except Exception as e:
            notes.append("subscriptions: %s" % str(e)[:120])

    if cfg.get("inactive_enabled"):
        try:
            with engine.begin() as c:
                rows = c.execute(text(
                    "SELECT client_id, MAX(entry_time) FROM visits "
                    "GROUP BY client_id")).fetchall()
                for cid, last in rows:
                    try:
                        d = datetime.datetime.fromisoformat(str(last)[:19]).date()
                    except Exception:
                        continue
                    gone = (today - d).days
                    if gone >= int(cfg.get("inactive_days", 14)):
                        body = _fmt(cfg["inactive_template"], days=gone)
                        if not _already(c, cid, body):
                            _mk_note(c, cid, str(cid), "reminder", body)
                            made += 1
        except Exception as e:
            notes.append("visits: %s" % str(e)[:120])

    result = {"ok": True, "created": made, "notes": notes}
    if cfg.get("auto_dispatch") and made:
        s, f = _dispatch_pending()
        result["sent"] = s
        result["failed"] = f
    return result


# ---------- демо ----------
@router.post("/messenger/demo")
def demo():
    _ensure()
    cid = "demo-" + uuid.uuid4().hex[:6]
    now = _now()
    with engine.begin() as c:
        c.execute(text("INSERT INTO messenger_chats(chat_id, client_name, source, "
                       "last_message, updated_at) VALUES(:c,:n,'max',:l,:t)"),
                  {"c": cid, "n": "Иван Петров (демо)",
                   "l": "Здравствуйте! До скольки работает бассейн?", "t": now})
        for d_, b_ in [("in", "Здравствуйте! До скольки работает бассейн?"),
                       ("out", "Добрый день! Бассейн работает до 22:00.")]:
            c.execute(text("INSERT INTO messenger_messages(id, chat_id, direction, "
                           "body, created_at) VALUES(:i,:c,:d,:b,:t)"),
                      {"i": uuid.uuid4().hex, "c": cid, "d": d_, "b": b_, "t": now})
        c.execute(text("INSERT INTO messenger_bindings(client_id, max_user_id, "
                       "client_name, role, bound_at) VALUES(:c,:m,:n,'client',:t) "
                       "ON CONFLICT(client_id) DO NOTHING"),
                  {"c": "demo-client-1", "m": "12345678",
                   "n": "Иван Петров (демо)", "t": now})
    return {"ok": True, "chat_id": cid}
