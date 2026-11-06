"""FitIntel Support Bot — каркас по ТЗ (фаза 1).

MAX (platform-api.max.ru) <-> webhook /bot/webhook <-> KB (docs/kb) + тикеты.
Платформу не изменяет: только GET к platform_api (через netns wireguard, порт 8002).

Идентификация клуба (ТЗ): по лицензии через API платформы —
  1) GET /platform/clubs          (X-Client-CN, матч клуба по префиксу ключа 12 симв.)
  2) GET /platform/clubs/{slug}/license -> status active|grace -> клуб привязан

TODO (фаза 2, после выдачи боевого токена MAX):
  - точный формат payload webhook MAX (reply/quote -> маршрутизация админских ответов)
  - механика вложений: upload скриншотов scr-*.png (MAX_UPLOAD_PATH)
  - расписание дежурств support_schedule -> выбор дежурного админа
"""
import logging, os
import httpx
import psycopg
from fastapi import FastAPI, Request, Header, HTTPException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("support-bot")

DATABASE_URL   = os.environ["DATABASE_URL"]
BOT_TOKEN      = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
MAX_API_BASE   = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru")
MAX_UPLOAD_PATH = os.environ.get("MAX_UPLOAD_PATH", "")
PLATFORM_API_URL = os.environ.get("PLATFORM_API_URL", "")  # http://platform-wireguard-1:8002
PLATFORM_ADMIN_CN = os.environ.get("PLATFORM_ADMIN_CN", "andrei@fitintel.local")
ALLOWED_LICENSE_STATUSES = {s.strip() for s in
    os.environ.get("ALLOWED_LICENSE_STATUSES", "active,grace").split(",") if s.strip()}
KB_TOP_N       = int(os.environ.get("KB_TOP_N", "3"))
KB_MIN_RANK    = float(os.environ.get("KB_MIN_RANK", "0.12"))

def conn():
    return psycopg.connect(DATABASE_URL)

# ---------- MAX ----------
async def max_send(user_id: str, text: str):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{MAX_API_BASE}/messages",
                         json={"recipient": {"user_id": user_id},
                               "message": {"text": text[:4000]}},
                         headers={"Authorization": BOT_TOKEN})
        r.raise_for_status()

async def max_send_screenshots(user_id: str, files: list):
    """Вложения: включается, когда MAX даст upload-эндпоинт (см. MAX_UPLOAD_PATH)."""
    if not (MAX_UPLOAD_PATH and files):
        return
    log.info("screenshots pending MAX upload mechanics: %s", files)

# ---------- platform: идентификация клуба по лицензии (только чтение) ----------
async def check_license(key: str):
    """Возвращает (ok, slug клуба). Внутренний вызов platform_api по сети platform_default."""
    if not PLATFORM_API_URL:
        return False, ""
    headers = {"X-Client-CN": f"CN={PLATFORM_ADMIN_CN}"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{PLATFORM_API_URL}/platform/clubs", headers=headers)
            if r.status_code != 200:
                log.warning("platform clubs list: HTTP %s", r.status_code)
                return False, ""
            slug = None
            for cl in r.json().get("clubs", []):
                pref = cl.get("license_key")  # хранится как 12 символов + '...'
                if pref and key.startswith(pref[:-3]):
                    slug = cl.get("slug")
                    break
            if not slug:
                return False, ""
            r2 = await c.get(f"{PLATFORM_API_URL}/platform/clubs/{slug}/license", headers=headers)
            if r2.status_code != 200:
                return False, ""
            st = r2.json().get("status")
            if st in ALLOWED_LICENSE_STATUSES:
                return True, slug
            return False, ""
    except Exception as e:
        log.warning("license check failed: %s", e)
        return False, ""

# ---------- KB ----------
TSQ = ("to_tsvector('russian', coalesce(question,'') || ' ' || coalesce(keywords,'')"
       " || ' ' || coalesce(answer,''))")

def kb_search(query: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            f"SELECT question, answer, screenshots, ts_rank({TSQ}, plainto_tsquery('russian', %s)) AS rank "
            f"FROM kb_articles WHERE {TSQ} @@ plainto_tsquery('russian', %s) "
            "ORDER BY rank DESC LIMIT %s", (query, query, KB_TOP_N))
        return cur.fetchall()

# ---------- tickets ----------
def get_or_open_ticket(user_id: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, club_id FROM tickets WHERE user_max_id=%s "
                    "AND status IN ('new','in_progress','waiting') "
                    "ORDER BY updated_at DESC LIMIT 1", (user_id,))
        return cur.fetchone()

def add_message(ticket_id, direction, body, author=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO ticket_messages (ticket_id, direction, body, author) VALUES (%s,%s,%s,%s)",
                    (ticket_id, direction, body, author))
        cur.execute("UPDATE tickets SET updated_at=now(), "
                    "status=CASE WHEN status='new' THEN 'in_progress' ELSE status END WHERE id=%s", (ticket_id,))
        cn.commit()

async def notify_admins(text: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT max_user_id FROM bot_admins WHERE active")
        admins = [r[0] for r in cur.fetchall()]
    for a in admins:
        try:
            await max_send(a, text)
        except Exception as e:
            log.warning("admin notify failed %s: %s", a, e)

# ---------- flows ----------
async def admin_reply(admin_id: str, text: str):
    """Админ пишет боту -> ответ уходит в последний открытый тикет.
    Маршрутизация по reply/quote уточняется под реальный payload MAX (фаза 2)."""
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, user_max_id FROM tickets WHERE status IN ('new','in_progress','waiting') "
                    "ORDER BY updated_at DESC LIMIT 1")
        row = cur.fetchone()
    if not row:
        await max_send(admin_id, "Нет открытых тикетов.")
        return
    ticket_id, user_id = row
    add_message(ticket_id, "out", text, author=admin_id)
    await max_send(user_id, text)

async def user_message(user_id: str, text: str):
    # 1) привязка клуба: первое сообщение = ключ лицензии (проверка через API платформы)
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT club_id FROM clubs_bound WHERE max_user_id=%s", (user_id,))
        bound = cur.fetchone()
    if not bound:
        ok, slug = await check_license(text.strip())
        if ok:
            with conn() as cn, cn.cursor() as cur:
                cur.execute("INSERT INTO clubs_bound (max_user_id, club_id, license_key) VALUES (%s,%s,%s) "
                            "ON CONFLICT (max_user_id) DO UPDATE SET club_id=EXCLUDED.club_id",
                            (user_id, slug, text.strip()))
                cn.commit()
            await max_send(user_id, f"Клуб привязан ({slug}). Задайте вопрос — отвечу из базы знаний; "
                                    "если решения нет, создам тикет инженеру.")
        else:
            await max_send(user_id, "Лицензия не найдена или не активна. "
                                    "Уточните ключ лицензии вашего клуба.")
        return

    club_id = bound[0]
    ticket = get_or_open_ticket(user_id)
    if not ticket:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("INSERT INTO tickets (user_max_id, club_id, subject) VALUES (%s,%s,%s) RETURNING id",
                        (user_id, club_id, text[:120]))
            ticket_id = cur.fetchone()[0]
            cn.commit()
    else:
        ticket_id = ticket[0]
    add_message(ticket_id, "in", text, author=user_id)

    hits = kb_search(text)
    if hits and float(hits[0][3]) >= KB_MIN_RANK:
        q, ans, shots, _rank = hits[0]
        await max_send(user_id, f"{ans}

— статья KB: «{q}»")
        await max_send_screenshots(user_id, list(shots or []))
    else:
        await max_send(user_id, "Похожей статьи в базе знаний нет — создал тикет, ответит инженер поддержки.")
        await notify_admins(f"🎫 Новый тикет от клуба {club_id}: {text[:200]}")

# ---------- http ----------
app = FastAPI(title="FitIntel Support Bot")

@app.get("/health")
def health():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        n = cur.fetchone()[0]
    return {"status": "ok", "kb_articles": n}

@app.post("/bot/webhook")
async def webhook(req: Request, x_webhook_secret: str = Header(default="")):
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad secret")
    data = await req.json()
    msg = data.get("message", data)  # формат MAX webhook уточняется по факту токена (фаза 2)
    sender = msg.get("sender") or {}
    user_id = str(sender.get("user_id") or msg.get("user_id") or "")
    text = (msg.get("text") or "").strip()
    if not user_id or not text:
        return {"ok": True}
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
        is_admin = cur.fetchone() is not None
    try:
        if is_admin:
            await admin_reply(user_id, text)
        else:
            await user_message(user_id, text)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
