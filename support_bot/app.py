"""FitIntel Support Bot — по ТЗ, контракт MAX сверен с dev.max.ru (06.11.2026).

- Webhook: подписка POST /subscriptions {url, update_types, secret};
  события приходят объектом Update, секрет — заголовок X-Max-Bot-Api-Secret.
- Исходящие: POST /messages?user_id=... {text, attachments}; заголовок Authorization: <token>.
- Вложения: POST /uploads?type=image -> {url, token} -> multipart на url ->
  attachments=[{type:"image", payload:{token}}] (PNG-скриншоты из docs/images/desktop).
- Идентификация клуба: GET /platform/clubs + /platform/clubs/{slug}/license
  (platform_api в netns wireguard, порт 8002; заголовок X-Client-CN).

Платформу не изменяет. TODO фаза 3: маршрутизация админских ответов по reply,
дежурства support_schedule.
"""
import logging, os, random
import httpx
import psycopg
from fastapi import FastAPI, Request, Header, HTTPException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("support-bot")

DATABASE_URL   = os.environ["DATABASE_URL"]
BOT_TOKEN      = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
MAX_API_BASE   = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru")
PLATFORM_API_URL = os.environ.get("PLATFORM_API_URL", "")  # http://platform-wireguard-1:8002
PLATFORM_ADMIN_CN = os.environ.get("PLATFORM_ADMIN_CN", "andrei@fitintel.local")
ALLOWED_LICENSE_STATUSES = {s.strip() for s in
    os.environ.get("ALLOWED_LICENSE_STATUSES", "active,grace").split(",") if s.strip()}
SCREENSHOTS_DIR = os.environ.get("SCREENSHOTS_DIR", "/screenshots")
KB_TOP_N       = int(os.environ.get("KB_TOP_N", "3"))
KB_MIN_RANK    = float(os.environ.get("KB_MIN_RANK", "0.12"))
MAX_SHOTS      = int(os.environ.get("MAX_SHOTS", "4"))

def conn():
    return psycopg.connect(DATABASE_URL)

# ---------- MAX: исходящие ----------
async def max_send(user_id: str, text: str, attachments: list | None = None):
    payload = {"text": text[:4000], "random_id": random.randint(1, 2**31 - 1)}
    if attachments:
        payload["attachments"] = attachments
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{MAX_API_BASE}/messages",
                         params={"user_id": user_id}, json=payload,
                         headers={"Authorization": BOT_TOKEN})
        r.raise_for_status()

async def max_upload_image(name: str, data: bytes):
    """Шаги 1-2 загрузки: получаем upload URL+token, заливаем multipart (ответ CDN не парсим)."""
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{MAX_API_BASE}/uploads", params={"type": "image"},
                         headers={"Authorization": BOT_TOKEN})
        r.raise_for_status()
        d = r.json()
        r2 = await c.post(d["url"], files={"data": (name, data, "image/png")})
        if r2.status_code >= 400:
            raise RuntimeError(f"cdn upload {r2.status_code}")
        return d["token"]

async def max_send_screenshots(user_id: str, files: list):
    atts = []
    for name in files[:MAX_SHOTS]:
        path = os.path.join(SCREENSHOTS_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                token = await max_upload_image(name, f.read())
            atts.append({"type": "image", "payload": {"token": token}})
        except Exception as e:
            log.warning("screenshot %s upload failed: %s", name, e)
    if atts:
        await max_send(user_id, "Скриншоты:", attachments=atts)

# ---------- platform: идентификация клуба по лицензии (только чтение) ----------
async def check_license(key: str):
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
    """Админ пишет боту -> ответ в последний открытый тикет.
    Точная маршрутизация по reply/quote — фаза 3 (посмотрим реальный Update)."""
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
        await max_send(user_id, f"{ans}\n\n— статья KB: «{q}»")
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
async def webhook(req: Request, x_max_bot_api_secret: str = Header(default="")):
    # секрет подписки MAX приходит в X-Max-Bot-Api-Secret (dev.max.ru, /subscriptions)
    if WEBHOOK_SECRET and x_max_bot_api_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad secret")
    data = await req.json()
    update_type = data.get("update_type", "")
    msg = data.get("message") or {}
    sender = msg.get("sender") or {}
    user_id = str(sender.get("user_id") or msg.get("user_id") or "")
    body = msg.get("body") or {}
    text = (body.get("text") or msg.get("text") or "").strip()

    if not user_id:
        return {"ok": True}   # служебные update-типы игнорируем

    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
        is_admin = cur.fetchone() is not None

    try:
        if update_type == "bot_started":
            await max_send(user_id, "Здравствуйте! Поддержка FitIntel Pro. "
                                    "Пришлите ключ лицензии вашего клуба (формат FIPRO-...), затем задайте вопрос.")
            return {"ok": True}
        if not text:
            return {"ok": True}
        if is_admin:
            await admin_reply(user_id, text)
        else:
            await user_message(user_id, text)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
