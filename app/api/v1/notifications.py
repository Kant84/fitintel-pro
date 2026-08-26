"""E17: омниканальные уведомления — email (SMTP), SMS (smsc.ru), Web Push."""
import json, smtplib, logging
from datetime import datetime
from email.mime.text import MIMEText
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()

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
        raise RuntimeError("DB engine not found")
    return _engine

def _ensure():
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS notification_settings (
            id INT PRIMARY KEY, updated_at TIMESTAMP DEFAULT NOW())"""))
    for col in ("email_enabled BOOLEAN DEFAULT FALSE", "smtp_host TEXT",
                "smtp_port INT DEFAULT 465", "smtp_user TEXT", "smtp_pass TEXT",
                "email_from TEXT", "sms_enabled BOOLEAN DEFAULT FALSE",
                "smsc_login TEXT", "smsc_pass TEXT", "smsc_sender TEXT",
                "webpush_enabled BOOLEAN DEFAULT FALSE", "vapid_public TEXT",
                "vapid_private TEXT", "vapid_sub TEXT",
                "digest_time VARCHAR(5) DEFAULT '09:00'"):
        try:
            with _eng().begin() as c:
                c.execute(text(f"ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS {col}"))
        except Exception as e:
            logger.warning("ensure col %s: %s", col.split()[0], str(e)[:100])
    try:
        with _eng().begin() as c:
            c.execute(text("INSERT INTO notification_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING"))
    except Exception:
        pass
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS notification_log (
            id BIGSERIAL PRIMARY KEY, channel VARCHAR(16), recipient TEXT,
            subject TEXT, body TEXT, status VARCHAR(16), error TEXT,
            created_at TIMESTAMP DEFAULT NOW())"""))
    with _eng().begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS webpush_subscriptions (
            id BIGSERIAL PRIMARY KEY, endpoint TEXT UNIQUE, keys_json TEXT,
            created_at TIMESTAMP DEFAULT NOW())"""))


def _settings():
    _ensure()
    with _eng().connect() as c:
        row = c.execute(text("SELECT * FROM notification_settings WHERE id=1")).mappings().first()
    return dict(row) if row else {}

def _log(channel, recipient, subject, body, status, error=None):
    try:
        with _eng().begin() as c:
            c.execute(text("""INSERT INTO notification_log (channel, recipient, subject, body, status, error)
                VALUES (:ch, :r, :s, :b, :st, :e)"""),
                {"ch": channel, "r": recipient, "s": (subject or "")[:250],
                 "b": (body or "")[:2000], "st": status, "e": (str(error) if error else None)})
    except Exception as e:
        logger.warning("notification log failed: %s", e)

def _send_email(to, subject, body):
    s = _settings()
    if not s.get("email_enabled"):
        return False, "email отключён в настройках"
    if not s.get("smtp_host"):
        return False, "smtp_host не задан"
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = s.get("email_from") or s.get("smtp_user") or ""
        msg["To"] = to
        port = int(s.get("smtp_port") or 465)
        if port == 465:
            srv = smtplib.SMTP_SSL(s["smtp_host"], port, timeout=20)
        else:
            srv = smtplib.SMTP(s["smtp_host"], port, timeout=20)
            srv.starttls()
        if s.get("smtp_user"):
            srv.login(s["smtp_user"], s.get("smtp_pass") or "")
        srv.sendmail(msg["From"], [to], msg.as_string())
        srv.quit()
        return True, None
    except Exception as e:
        return False, str(e)[:300]

def _send_sms(phone, message):
    s = _settings()
    if not s.get("sms_enabled"):
        return False, "sms отключён в настройках"
    if not s.get("smsc_login"):
        return False, "smsc_login не задан"
    try:
        import requests as _rq
        r = _rq.get("https://smsc.ru/sys/send.php", params={
            "login": s["smsc_login"], "psw": s.get("smsc_pass") or "",
            "phones": phone, "mes": message,
            "sender": s.get("smsc_sender") or "", "fmt": 3, "charset": "utf-8"}, timeout=20)
        data = r.json()
        if "error" in data:
            return False, data["error"]
        return True, None
    except Exception as e:
        return False, str(e)[:300]

def _send_webpush(title, body):
    s = _settings()
    if not s.get("webpush_enabled"):
        return False, "webpush отключён в настройках"
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return False, "pywebpush не установлен (pip install pywebpush)"
    ok, errs = 0, []
    with _eng().connect() as c:
        subs = c.execute(text("SELECT endpoint, keys_json FROM webpush_subscriptions")).all()
    for ep, keys in subs:
        try:
            webpush({"endpoint": ep, "keys": json.loads(keys)},
                    json.dumps({"title": title, "body": body}, ensure_ascii=False),
                    vapid_private_key=s.get("vapid_private"),
                    vapid_claims={"sub": s.get("vapid_sub") or "mailto:admin@fitintel.local"})
            ok += 1
        except Exception as e:
            errs.append(str(e)[:150])
    if ok:
        return True, None
    return False, "; ".join(errs) or "нет подписок"

class TestIn(BaseModel):
    channel: str            # email | sms | webpush
    to: str = ""
    message: str = "Тестовое уведомление FitIntel Pro"

@router.get("/notify/settings")
def get_settings():
    s = _settings()
    for k in ("smtp_pass", "smsc_pass", "vapid_private"):
        if s.get(k):
            s[k] = "***"
    return s

@router.post("/notify/settings")
def set_settings(body: dict):
    _ensure()
    allowed = {"email_enabled", "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "email_from",
               "sms_enabled", "smsc_login", "smsc_pass", "smsc_sender",
               "webpush_enabled", "vapid_public", "vapid_private", "vapid_sub", "digest_time"}
    sets, params = [], {}
    for k, v in body.items():
        if k in allowed:
            if k in ("smtp_pass", "smsc_pass", "vapid_private") and v == "***":
                continue
            sets.append(f"{k} = :{k}")
            params[k] = v
    if sets:
        with _eng().begin() as c:
            c.execute(text(f"UPDATE notification_settings SET {', '.join(sets)}, updated_at=NOW() WHERE id=1"), params)
    return {"ok": True}

@router.post("/notify/test")
def test_send(body: TestIn):
    ch = body.channel.lower()
    if ch == "email":
        ok, err = _send_email(body.to, "FitIntel Pro — тест", body.message)
    elif ch == "sms":
        ok, err = _send_sms(body.to, body.message)
    elif ch == "webpush":
        ok, err = _send_webpush("FitIntel Pro", body.message)
    else:
        return {"ok": False, "error": "channel: email|sms|webpush"}
    _log(ch, body.to or "(all)", "test", body.message, "sent" if ok else "error", err)
    return {"ok": ok, "error": err}

@router.get("/notify/log")
def get_log(limit: int = 50):
    _ensure()
    with _eng().connect() as c:
        rows = c.execute(text("SELECT id, channel, recipient, subject, status, error, created_at FROM notification_log ORDER BY id DESC LIMIT :n"), {"n": min(limit, 200)}).mappings().all()
    return [dict(r) for r in rows]

@router.post("/notify/webpush/subscribe")
def wp_subscribe(body: dict):
    _ensure()
    ep = body.get("endpoint")
    if not ep:
        return {"ok": False, "error": "endpoint обязателен"}
    with _eng().begin() as c:
        c.execute(text("""INSERT INTO webpush_subscriptions (endpoint, keys_json) VALUES (:e, :k)
            ON CONFLICT (endpoint) DO UPDATE SET keys_json=EXCLUDED.keys_json"""),
            {"e": ep, "k": json.dumps(body.get("keys") or {})})
    return {"ok": True}

@router.post("/notify/digest")
def send_digest():
    """Ежедневный дайджест на email: посещения/выручка/клиенты за сегодня."""
    with _eng().connect() as c:
        def _cnt(q):
            try:
                return c.execute(text(q)).scalar() or 0
            except Exception:
                return 0
        clients = _cnt("SELECT COUNT(*) FROM clients")
        visits = _cnt("SELECT COUNT(*) FROM visits WHERE created_at::date = CURRENT_DATE")
        revenue = _cnt("SELECT COALESCE(SUM(amount),0) FROM payments WHERE created_at::date = CURRENT_DATE")
    s = _settings()
    to = s.get("email_from") or s.get("smtp_user") or ""
    body = (f"Дайджест FitIntel Pro за {datetime.now():%d.%m.%Y}\n\n"
            f"Клиентов в базе: {clients}\nПосещений сегодня: {visits}\nВыручка сегодня: {revenue} руб.")
    ok, err = _send_email(to, f"FitIntel дайджест {datetime.now():%d.%m.%Y}", body)
    _log("email", to, "digest", body, "sent" if ok else "error", err)
    return {"ok": ok, "error": err, "stats": {"clients": clients, "visits_today": visits, "revenue_today": revenue}}

@router.get("/notify/contacts")
def notify_contacts():
    """Список контактов клиентов для выбора получателя (без ручного ввода)."""
    out = []
    try:
        with _eng().connect() as c:
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='clients'"))}
        nm = next((x for x in ("full_name", "name", "first_name") if x in cols), None)
        em = next((x for x in ("email", "e_mail", "mail") if x in cols), None)
        ph = next((x for x in ("phone", "phone_number", "tel", "mobile") if x in cols), None)
        sel = [x for x in (nm, em, ph) if x]
        if not sel:
            return []
        with _eng().connect() as c:
            rows = c.execute(text(f"SELECT {', '.join(sel)} FROM clients ORDER BY 1 LIMIT 500")).mappings().all()
        for r in rows:
            d = dict(r)
            out.append({"name": str(d.get(nm) or "") if nm else "",
                        "email": str(d.get(em) or "") if em else "",
                        "phone": str(d.get(ph) or "") if ph else ""})
    except Exception as e:
        return {"error": str(e)[:200]}
    return out


# === E17_SCHEDULER: авто-дайджест ежедневно в digest_time ===
import threading as _th, time as _time, urllib.request as _ur
from datetime import datetime as _dt, date as _date

def _e17_scheduler():
    last = {}
    while True:
        try:
            with _eng().begin() as c:
                row = c.execute(text("SELECT digest_time, email_enabled FROM notification_settings WHERE id=1")).mappings().first()
            if row and row.get("email_enabled"):
                dt = str(row.get("digest_time") or "08:00")[:5]
                now = _dt.now().strftime("%H:%M")
                today = str(_date.today())
                if now == dt and last.get("d") != today:
                    last["d"] = today
                    req = _ur.Request("http://localhost:8001/api/v1/notify/digest",
                                      data=b"{}", headers={"Content-Type": "application/json"})
                    _ur.urlopen(req, timeout=60)
                    print("[E17] авто-дайджест отправлен", now)
        except Exception as e:
            print("[E17] scheduler:", str(e)[:120])
        _time.sleep(60)

_th.Thread(target=_e17_scheduler, daemon=True).start()
print("[E17] scheduler OK")
