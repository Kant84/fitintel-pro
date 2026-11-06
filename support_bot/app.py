"""FitIntel Support Bot — v5: парсинг интента, нормализация вопросов, fuzzy KB.

Изменения v5:
- Слой парсинга: приветствие / фрустрация / вопрос. Агрессия -> спокойный ответ,
  бот НИКОГДА не повторяет чужие фразы (убрано эхо админской ветки).
- Нормализация вопроса: стоп-слова, пунктуация; tsquery + trigram-similarity fallback
  (формулировки вида «как делать платежи» находят статью «как провести платёж»).
- Тикет создаётся ТОЛЬКО при промахе KB (раньше — всегда).
- Админ: ответ в тикет строго по '#ТОКЕН текст' или команде 'тикеты'; эвристика
  «последний открытый тикет» удалена (была причиной эха).
- Привязка клуба: deeplink ?start=<префикс ключа> (desktop) / ключ текстом (fallback).
- Сырые Update логируются (формат payload фиксируем по факту).
"""
import json, logging, os, random, re
import httpx
import psycopg
from fastapi import FastAPI, Request, Header, HTTPException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("support-bot")

DATABASE_URL   = os.environ["DATABASE_URL"]
BOT_TOKEN      = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
MAX_API_BASE   = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru")
PLATFORM_API_URL = os.environ.get("PLATFORM_API_URL", "")
PLATFORM_ADMIN_CN = os.environ.get("PLATFORM_ADMIN_CN", "andrei@fixintel.ru")
ALLOWED_LICENSE_STATUSES = {s.strip() for s in
    os.environ.get("ALLOWED_LICENSE_STATUSES", "active,grace").split(",") if s.strip()}
SCREENSHOTS_DIR = os.environ.get("SCREENSHOTS_DIR", "/screenshots")
KB_TOP_N       = int(os.environ.get("KB_TOP_N", "3"))
KB_MIN_RANK    = float(os.environ.get("KB_MIN_RANK", "0.12"))
SIM_MIN        = float(os.environ.get("KB_MIN_SIM", "0.28"))
MAX_SHOTS      = int(os.environ.get("MAX_SHOTS", "4"))

STOP = {"как","можно","подскажите","пожалуйста","помогите","помощь","здравствуйте",
        "здравствуй","добрый","доброе","добрый","день","вечер","утро","спасибо",
        "заранее","сделать","делать","надо","нужно","нужна","нужно","хочу","хочется",
        "почему","зачем","кто","что","где","когда","какой","какая","какие","чем","ли",
        "у","в","на","по","за","из","с","со","к","не","ни","же","бы","а","и","но","это","то"}
GREETINGS = {"привет","здравствуйте","здравствуй","добрый","доброе","добрый","добрый",
             "hello","hi","хай","хелло","салют"}
FRUSTRATED = {"гонишь","очумел","бред","чушь","хрень","ерунда","отстой","задолбал",
              "исправьте","почините","ты что","вы что","алле","але","эй","слушай",
              "что за","никак","ни фига","нифига","капец","бесит"}

def normalize(q: str) -> str:
    q = re.sub(r"[^\w\s-]", " ", q.lower(), flags=re.UNICODE)
    return " ".join(w for w in q.split() if w not in STOP)

def classify(text: str) -> str:
    t = text.lower().strip()
    words = set(re.findall(r"[а-яa-z]+", t))
    if t.rstrip("!?. ") in GREETINGS or (words and words <= GREETINGS):
        return "greeting"
    if any(a in t for a in FRUSTRATED):
        return "frustrated"
    return "question"

def conn():
    return psycopg.connect(DATABASE_URL)

# ---------- MAX ----------
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

# ---------- platform ----------
async def check_license(key: str):
    if not PLATFORM_API_URL or len(key) < 12:
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
                pref = cl.get("license_key")
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

# ---------- KB: fts + trigram fallback ----------
TSQ = ("to_tsvector('russian', coalesce(question,'') || ' ' || coalesce(keywords,'')"
       " || ' ' || coalesce(answer,''))")

def kb_search(query: str):
    """Возвращает (question, answer, screenshots, score) лучшей статьи или None."""
    q = normalize(query)
    if not q:
        return None
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            f"SELECT question, answer, screenshots, ts_rank({TSQ}, plainto_tsquery('russian', %s)) "
            f"FROM kb_articles WHERE {TSQ} @@ plainto_tsquery('russian', %s) "
            "ORDER BY 4 DESC LIMIT 1", (q, q))
        row = cur.fetchone()
        if row and float(row[3]) >= KB_MIN_RANK:
            return row[0], row[1], row[2], float(row[3])
        # trigram fallback: перестановки/синонимы формулировок
        cur.execute(
            "SELECT question, answer, screenshots, "
            "GREATEST(similarity(question, %s), similarity(coalesce(keywords,''), %s), "
            "similarity(question, %s)) AS sim FROM kb_articles "
            "WHERE question %% %s OR coalesce(keywords,'') %% %s "
            "ORDER BY sim DESC LIMIT 1", (query, query, q, query, q))
        row = cur.fetchone()
        if row and float(row[3]) >= SIM_MIN:
            return row[0], row[1], row[2], float(row[3])
    return None

# ---------- tickets ----------
def add_message(ticket_id, direction, body, author=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO ticket_messages (ticket_id, direction, body, author) VALUES (%s,%s,%s,%s)",
                    (ticket_id, direction, body, author))
        cur.execute("UPDATE tickets SET updated_at=now(), "
                    "status=CASE WHEN status='new' THEN 'in_progress' ELSE status END WHERE id=%s", (ticket_id,))
        cn.commit()

def open_tickets():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, club_id, subject, status FROM tickets "
                    "WHERE status IN ('new','in_progress','waiting') ORDER BY updated_at DESC LIMIT 10")
        return cur.fetchall()

async def notify_admins(text: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT max_user_id FROM bot_admins WHERE active")
        admins = [r[0] for r in cur.fetchall()]
    for a in admins:
        try:
            await max_send(a, text)
        except Exception as e:
            log.warning("admin notify failed %s: %s", a, e)

# ---------- admin commands ----------
ADMIN_REPLY_RE = re.compile(r"^\s*#([0-9A-Za-z]{4,16})\s+(.*)$", re.S)
TICKETS_CMD = {"тикеты", "/tickets", "тикеты!", "tickets"}

async def admin_command(admin_id: str, text: str) -> bool:
    """Маршрутизация админа: '#ТОКЕН текст' -> в тикет; 'тикеты' -> список."""
    t = text.strip()
    if t.lower() in TICKETS_CMD:
        rows = open_tickets()
        if not rows:
            await max_send(admin_id, "Открытых тикетов нет ✓")
            return True
        lines = ["Открытые тикеты (ответ: #ТОКЕН текст):"]
        for tid, club, subj, st in rows:
            lines.append(f"#{str(tid)[:8]} [{st}] {club}: {subj[:60]}")
        await max_send(admin_id, "\n".join(lines))
        return True
    m = ADMIN_REPLY_RE.match(text)
    if not m:
        return False
    tok, body = m.group(1), m.group(2).strip()
    if not body:
        return True
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, user_max_id FROM tickets WHERE id::text LIKE %s "
                    "AND status IN ('new','in_progress','waiting') LIMIT 1", (tok + "%",))
        row = cur.fetchone()
    if not row:
        await max_send(admin_id, f"Тикет #{tok} не найден среди открытых. Команда «тикеты» — список.")
        return True
    ticket_id, user_id = row
    add_message(ticket_id, "out", body, author=admin_id)
    await max_send(user_id, body)
    await max_send(admin_id, f"✓ Ответ ушёл в тикет #{str(ticket_id)[:8]}")
    return True

# ---------- flows ----------
async def bind_club(user_id: str, key: str, via: str) -> bool:
    ok, slug = await check_license(key.strip())
    if not ok:
        return False
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO clubs_bound (max_user_id, club_id, license_key) VALUES (%s,%s,%s) "
                    "ON CONFLICT (max_user_id) DO UPDATE SET club_id=EXCLUDED.club_id",
                    (user_id, slug, key.strip()[:64]))
        cn.commit()
    src = "через desktop" if via == "deeplink" else "по ключу лицензии"
    await max_send(user_id, f"Клуб привязан ({slug}) — {src}. Задайте вопрос: настройки, права, "
                            "платежи, ошибки. Если решения нет в базе знаний — создам тикет инженеру.")
    return True

async def ask_and_answer(user_id: str, club_id: str, text: str):
    """Поиск в KB; тикет — только при промахе."""
    hit = kb_search(text)
    if hit:
        q, ans, shots, _score = hit
        await max_send(user_id, f"{ans}\n\n— статья KB: «{q}»")
        await max_send_screenshots(user_id, list(shots or []))
        return
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO tickets (user_max_id, club_id, subject, status) VALUES (%s,%s,%s,'new') RETURNING id",
                    (user_id, club_id, text[:120]))
        ticket_id = cur.fetchone()[0]
        cn.commit()
    add_message(ticket_id, "in", text, author=user_id)
    tid8 = str(ticket_id)[:8]
    await max_send(user_id, "Похожей статьи в базе знаний нет — создал тикет, ответит инженер поддержки.")
    await notify_admins(f"🎫 Тикет #{tid8} от клуба {club_id}: {text[:180]}\n"
                        f"Ответить: #{tid8} <текст>")

async def user_message(user_id: str, text: str, payload: str = "", is_admin: bool = False):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT club_id FROM clubs_bound WHERE max_user_id=%s", (user_id,))
        bound = cur.fetchone()

    if not bound:
        if payload:
            if await bind_club(user_id, payload, "deeplink"):
                return
            await max_send(user_id, "Не смог опознать клуб по данным из desktop. "
                                    "Напишите нам: support@fixintel.ru.")
            return
        if text.strip().startswith("FIPRO-"):
            if await bind_club(user_id, text, "text"):
                return
            await max_send(user_id, "Лицензия не найдена или не активна. Проверьте, что ключ скопирован целиком.")
            return
        await max_send(user_id, "Здравствуйте! Поддержка FitIntel Pro. Откройте этот чат из desktop-клиента "
                                "(Помощь → Поддержка разработчика → Открыть MAX) — клуб подключится автоматически. "
                                "Или пришлите ключ лицензии вашего клуба.")
        return

    club_id = bound[0]
    intent = classify(text)
    if intent == "greeting":
        await max_send(user_id, "Здравствуйте! Задайте вопрос — настройки, права, платежи, ошибки. "
                                "Команда «тикеты» — ваши обращения к инженерам.")
        return
    if intent == "frustrated":
        await max_send(user_id, "Понимаю, ситуация неприятная. Опишите, пожалуйста, парой фраз: "
                                "какой экран, что делали, что получилось в итоге — сразу поищу решение.")
        # и продолжаем как вопрос: поиск по очищенному тексту
    await ask_and_answer(user_id, club_id, text)

# ---------- http ----------
app = FastAPI(title="FitIntel Support Bot")

@app.get("/health")
def health():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        n = cur.fetchone()[0]
    return {"status": "ok", "kb_articles": n}

def extract_payload(data: dict, msg: dict, body: dict) -> str:
    text = (body.get("text") or msg.get("text") or "").strip()
    for pfx in ("/start", "!start", "/старт"):
        if text.startswith(pfx):
            rest = text[len(pfx):].strip()
            if rest:
                return rest
    for src in (msg, body, data):
        for k in ("payload", "start_payload", "start_param", "startapp"):
            v = src.get(k)
            if v:
                return str(v)
    return ""

@app.post("/bot/webhook")
async def webhook(req: Request, x_max_bot_api_secret: str = Header(default="")):
    if WEBHOOK_SECRET and x_max_bot_api_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad secret")
    data = await req.json()
    log.info("update: %s", json.dumps(data, ensure_ascii=False)[:500])
    update_type = data.get("update_type", "")
    msg = data.get("message") or {}
    sender = msg.get("sender") or {}
    user_id = str(sender.get("user_id") or msg.get("user_id") or "")
    body = msg.get("body") or {}
    text = (body.get("text") or msg.get("text") or "").strip()
    payload = extract_payload(data, msg, body)

    if not user_id:
        return {"ok": True}

    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
        is_admin = cur.fetchone() is not None

    try:
        if update_type == "bot_started":
            if payload:
                await user_message(user_id, "", payload)
            else:
                await max_send(user_id, "Здравствуйте! Поддержка FitIntel Pro. Если вы зашли из desktop-клиента, "
                                        "клуб привяжется автоматически — просто нажмите «Начать». Далее задавайте вопрос.")
            return {"ok": True}
        if not text and not payload:
            return {"ok": True}
        if is_admin and text:
            if await admin_command(user_id, text):
                return {"ok": True}
        await user_message(user_id, text, payload, is_admin=is_admin)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
