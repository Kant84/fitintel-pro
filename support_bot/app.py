"""FitIntel Support Bot — v6: сценарии поддержки по регламенту продукта.

Регламент (07.11.2026):
- Клиент НИКОГДА не видит слова «тикет». Нет ответа -> «Передал вопрос инженеру поддержки»;
  просьба специалиста -> «Вопрос передал специалисту поддержки».
- Просьба связать со специалистом: до 2 уточняющих вопросов (тема/экран/что происходит),
  затем админу уходит вопрос С уточнениями.
- Грубые обращения -> таблица incidents (статистика по пользователю), команда «статистика».
- Промахи KB -> tickets.kb_miss=true (база пробелов знаний).
- Поиск KB: FTS по заголовку+ключам с синонимами, word_similarity fallback.
- Привязка клуба: deeplink ?start=<префикс ключа>[~login сотрудника] из desktop / ключ текстом.
- Админ: '#ТОКЕН текст' -> в обращение, 'тикеты'/'обращения' -> список. Эха нет.
"""
import asyncio, json, logging, os, random, re, time
import httpx
import psycopg
from fastapi import FastAPI, Request, Header, HTTPException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("support-bot")

NL = chr(10)  # перевод строки для сообщений

DATABASE_URL   = os.environ["DATABASE_URL"]
BOT_TOKEN      = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
MAX_API_BASE   = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru")
PLATFORM_API_URL = os.environ.get("PLATFORM_API_URL", "")
PLATFORM_ADMIN_CN = os.environ.get("PLATFORM_ADMIN_CN", "andrei@fixintel.ru")
ALLOWED_LICENSE_STATUSES = {s.strip() for s in
    os.environ.get("ALLOWED_LICENSE_STATUSES", "active,grace").split(",") if s.strip()}
SCREENSHOTS_DIR = os.environ.get("SCREENSHOTS_DIR", "/screenshots")
KB_MIN_RANK    = float(os.environ.get("KB_MIN_RANK", "0.03"))
SIM_MIN        = float(os.environ.get("KB_MIN_SIM", "0.3"))
MAX_SHOTS      = int(os.environ.get("MAX_SHOTS", "4"))
ESCALATE_TIMEOUT = float(os.environ.get("ESCALATE_TIMEOUT", "600"))

STOP = {"как","можно","подскажите","пожалуйста","помогите","помощь","здравствуйте",
        "здравствуй","добрый","доброе","день","вечер","утро","спасибо","заранее",
        "сделать","делать","надо","нужно","нужна","хочу","хочется","почему","зачем",
        "кто","что","где","когда","какой","какая","какие","чем","ли",
        "у","в","на","по","за","из","с","со","к","не","ни","же","бы","а","и","но","это","то"}
GREETINGS = {"привет","здравствуйте","здравствуй","добрый","доброе","hello","hi","хай","хелло","салют"}
FRUSTRATED = {"гонишь","очумел","бред","чушь","хрень","ерунда","отстой","задолбал",
              "исправьте","почините","ты что","вы что","алле","але","эй","слушай",
              "что за","нифига","капец","бесит","уроды","тупой","тупая","кривой"}
ESCALATE = {"оператор","живой","живого","человек","специалист","админ","администратор",
            "свяжите","свяжи","позовите","диспетчер","горячая линия","поддержку позови",
            "нужен человек","соедините"}
# синонимы: формы запроса -> лексемы KB (OR-дополнение tsquery)
SYN = {"платеж":"оплат","платежи":"оплат","платёж":"оплат","оплат":"платеж",
       "оплата":"платеж","оплатить":"платеж","заплат":"платеж",
       "абонемент":"подписк","замороз":"заморозк","размороз":"заморозк",
       "турникет":"проход","проход":"турникет","вход":"проход","браслет":"проход",
       "касса":"ккт","ккт":"касса чек","чек":"ккт касса",
       "скидк":"бонус","бонус":"скидк","тренер":"услуг расписан",
       "вендинг":"автомат магазин","автомат":"вендинг магазин"}

def normalize(q: str) -> str:
    q = re.sub(r"[^\w\s-]", " ", q.lower(), flags=re.UNICODE).replace("-", " ")
    return " ".join(w for w in q.split() if w not in STOP)

def to_tsquery(q: str) -> str:
    toks = set(q.split())
    for t in list(toks):
        for src, dst in SYN.items():
            if t.startswith(src):
                toks.update(dst.split())
    return " | ".join(sorted(toks))

def classify(text: str) -> str:
    t = text.lower().strip()
    words = set(re.findall(r"[а-яa-z]+", t))
    if t.rstrip("!?.") in GREETINGS or (words and words <= GREETINGS):
        return "greeting"
    if any(a in t for a in ESCALATE):
        return "escalate"
    if any(a in t for a in FRUSTRATED):
        return "frustrated"
    return "question"

def conn():
    return psycopg.connect(DATABASE_URL)

def init_schema():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS incidents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_max_id text NOT NULL, club_id text, text text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now())""")
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS kb_miss boolean NOT NULL DEFAULT false")
        cn.commit()

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
        log.info("uploads resp: %s", json.dumps(d, ensure_ascii=False)[:400])
        url = d["url"]
        token = d.get("token")
        if not token and isinstance(d.get("photos"), dict):
            for v in d["photos"].values():
                if isinstance(v, dict) and v.get("token"):
                    token = v["token"]
                    break
        if not token:
            raise RuntimeError(f"no token in uploads response: {list(d.keys())}")
        r2 = await c.post(url, files={"data": (name, data, "image/png")})
        if r2.status_code >= 400:
            raise RuntimeError(f"cdn upload {r2.status_code}")
        return token

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
        await asyncio.sleep(1)  # CDN должен прогреть файл (attachment.not.ready)
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
            return (r2.json().get("status") in ALLOWED_LICENSE_STATUSES), slug
    except Exception as e:
        log.warning("license check failed: %s", e)
        return False, ""

# ---------- KB: FTS (заголовок+ключи, с синонимами) + word_similarity ----------
TSQ_SHORT = "to_tsvector('russian', question || ' ' || coalesce(keywords,''))"

def kb_search(query: str):
    q = normalize(query)
    if not q:
        return None
    tsq = to_tsquery(q)
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            f"SELECT question, answer, screenshots, "
            f"ts_rank({TSQ_SHORT}, to_tsquery('russian', %s)) "
            f"FROM kb_articles WHERE {TSQ_SHORT} @@ to_tsquery('russian', %s) "
            "ORDER BY 4 DESC LIMIT 1", (tsq, tsq))
        row = cur.fetchone()
        if row and float(row[3]) >= KB_MIN_RANK:
            return row[0], row[1], row[2], float(row[3])
        cur.execute(
            "SELECT question, answer, screenshots, word_similarity(question, %s) AS sim "
            "FROM kb_articles WHERE question %% %s ORDER BY sim DESC LIMIT 1", (query, query))
        row = cur.fetchone()
        if row and float(row[3]) >= SIM_MIN:
            return row[0], row[1], row[2], float(row[3])
    return None

# ---------- tickets / incidents ----------
def add_message(ticket_id, direction, body, author=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO ticket_messages (ticket_id, direction, body, author) VALUES (%s,%s,%s,%s)",
                    (ticket_id, direction, body, author))
        cur.execute("UPDATE tickets SET updated_at=now(), "
                    "status=CASE WHEN status='new' THEN 'in_progress' ELSE status END WHERE id=%s", (ticket_id,))
        cn.commit()

def create_ticket(user_id, club_id, text, kb_miss, staff=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO tickets (user_max_id, club_id, subject, status, kb_miss) "
                    "VALUES (%s,%s,%s,'new',%s) RETURNING id", (user_id, club_id, text[:120], kb_miss))
        tid = cur.fetchone()[0]
        cn.commit()
    return tid

def open_tickets():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, club_id, subject, status FROM tickets "
                    "WHERE status IN ('new','in_progress','waiting') ORDER BY updated_at DESC LIMIT 10")
        return cur.fetchall()

def log_incident(user_id, club_id, text):
    try:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("INSERT INTO incidents (user_max_id, club_id, text) VALUES (%s,%s,%s)",
                        (user_id, club_id, text[:300]))
            cn.commit()
    except Exception as e:
        log.warning("incident log failed: %s", e)

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
LIST_CMD = {"тикеты","обращения","/tickets","tickets"}
STAT_CMD = {"статистика","/stats","стат"}

async def admin_command(admin_id: str, text: str) -> bool:
    t = text.strip()
    low = t.lower()
    if low in STAT_CMD:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT user_max_id, club_id, count(*) FROM incidents "
                        "GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            await max_send(admin_id, "Грубых обращений не зафиксировано ✓")
            return True
        lines = ["Статистика грубых обращений (по пользователям):"]
        for uid, club, n in rows:
            lines.append(f"{uid} (клуб {club}): {n}")
        await max_send(admin_id, NL.join(lines))
        return True
    if low in LIST_CMD:
        rows = open_tickets()
        if not rows:
            await max_send(admin_id, "Открытых обращений нет ✓")
            return True
        lines = ["Открытые обращения (ответ: #ТОКЕН текст):"]
        for tid, club, subj, st in rows:
            lines.append(f"#{str(tid)[:8]} [{st}] {club}: {subj[:60]}")
        await max_send(admin_id, NL.join(lines))
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
        await max_send(admin_id, f"Обращение #{tok} не найдено среди открытых. Команда «обращения» — список.")
        return True
    ticket_id, user_id = row
    add_message(ticket_id, "out", body, author=admin_id)
    await max_send(user_id, body)
    await max_send(admin_id, f"✓ Ответ ушёл в обращение #{str(ticket_id)[:8]}")
    return True

# ---------- flows ----------
PENDING_ESCALATE = {}  # user_id -> {"t": ts, "attempts": int, "orig": str, "extra": [..], "club": str, "staff": str}

async def bind_club(user_id: str, key: str, via: str) -> bool:
    ok, slug = await check_license(key.strip())
    if not ok:
        return False
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO clubs_bound (max_user_id, club_id, license_key) VALUES (%s,%s,%s) "
                    "ON CONFLICT (max_user_id) DO UPDATE SET club_id=EXCLUDED.club_id",
                    (user_id, slug, key.strip()[:64]))
        cn.commit()
    await max_send(user_id, "Здравствуйте! Клуб подключён. Задайте вопрос — настройки, права, "
                            "платежи, ошибки. Отвечаю мгновенно по базе знаний; если решения нет — "
                            "передам вопрос инженеру.")
    return True

async def answer_or_forward(user_id: str, club_id: str, text: str, staff: str = ""):
    """KB-ответ клиенту; при промахе — переадресация инженеру (без слова «тикет»)."""
    hit = kb_search(text)
    if hit:
        q, ans, shots, _s = hit
        await max_send(user_id, f"{ans}")
        await max_send_screenshots(user_id, list(shots or []))
        return
    tid = create_ticket(user_id, club_id, text, kb_miss=True, staff=staff)
    add_message(tid, "in", text, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    await max_send(user_id, "Передал вопрос инженеру поддержки. Ответ придёт сюда.")
    await notify_admins(f"❓ Пробел знаний, клуб {club_id}{who}: {text[:180]}" + NL +
                        f"Ответить: #{str(tid)[:8]} <текст>")

async def escalate_flow(user_id: str, club_id: str, text: str, staff: str = ""):
    """Просьба специалиста: до 2 уточнений, затем передача с уточнениями."""
    st = PENDING_ESCALATE.get(user_id)
    if not st or time.time() - st["t"] > ESCALATE_TIMEOUT:
        PENDING_ESCALATE[user_id] = {"t": time.time(), "attempts": 0, "orig": text, "extra": [],
                                     "club": club_id, "staff": staff}
        await max_send(user_id, "Понял, соединяю со специалистом. Чтобы ответ был точным, уточните: "
                                "какой раздел/экран и что именно происходит?")
        return
    st["t"] = time.time()
    st["attempts"] += 1
    if text.strip():
        st["extra"].append(text.strip())
    if st["attempts"] < 2 and len(text.strip()) < 15:
        await max_send(user_id, "Принял. Ещё деталь: что успели заметить — текст ошибки или момент, "
                                "когда это началось? (можно коротко)")
        return
    summary = st["orig"]
    if st["extra"]:
        summary += " | Уточнения: " + "; ".join(st["extra"])
    PENDING_ESCALATE.pop(user_id, None)
    tid = create_ticket(user_id, club_id, summary, kb_miss=False, staff=staff)
    add_message(tid, "in", summary, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    await max_send(user_id, "Вопрос передал специалисту поддержки. Ответ придёт сюда.")
    await notify_admins(f"🆘 Запрос специалиста, клуб {club_id}{who}: {summary[:220]}" + NL +
                        f"Ответить: #{str(tid)[:8]} <текст>")

async def user_message(user_id: str, text: str, payload: str = ""):
    staff = ""
    if payload and "~" in payload:  # формат: <префикс ключа>~<login сотрудника>
        payload, staff = payload.split("~", 1)
        staff = staff.strip()[:64]
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT club_id FROM clubs_bound WHERE max_user_id=%s", (user_id,))
        bound = cur.fetchone()

    if not bound:
        if payload:
            if await bind_club(user_id, payload, "deeplink"):
                return
            await max_send(user_id, "Не смог опознать клуб. Напишите нам: support@fixintel.ru.")
            return
        if text.strip().startswith("FIPRO-"):
            if await bind_club(user_id, text, "text"):
                return
            await max_send(user_id, "Ключ не распознан или лицензия не активна. Проверьте, что ключ скопирован целиком.")
            return
        await max_send(user_id, "Здравствуйте! Это поддержка FitIntel Pro. Откройте чат кнопкой «Поддержка "
                                "разработчика» в desktop-клиенте — клуб подключится автоматически, и можно "
                                "сразу писать вопрос.")
        return

    club_id = bound[0]
    intent = classify(text)
    if intent == "greeting":
        await max_send(user_id, "Здравствуйте! Задайте вопрос — настройки, права, платежи, ошибки.")
        return
    if intent == "escalate":
        await escalate_flow(user_id, club_id, text, staff)
        return
    if intent == "frustrated":
        log_incident(user_id, club_id, text)
        await max_send(user_id, "Понимаю, ситуация неприятная. Опишите парой фраз: какой экран, что делали, "
                                "что получилось в итоге — сразу поищу решение.")
    await answer_or_forward(user_id, club_id, text, staff)

# ---------- http ----------
app = FastAPI(title="FitIntel Support Bot")

@app.on_event("startup")
def _startup():
    init_schema()

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
                await max_send(user_id, "Здравствуйте! Поддержка FitIntel Pro. Задавайте вопрос — "
                                        "настройки, права, платежи, ошибки.")
            return {"ok": True}
        if not text and not payload:
            return {"ok": True}
        if is_admin and text:
            if await admin_command(user_id, text):
                return {"ok": True}
        await user_message(user_id, text, payload)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
