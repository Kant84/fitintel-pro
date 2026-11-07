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
- v8: многопользовательский переключатель ролей (только для admin): inline-клавиатура
  «👤 Пользователь ПО / 🛠 Админ поддержки / ⚙️ Авто», режим в таблице user_modes.
  Команда «режим» показывает переключатель. Кнопки callback: payload "mode:<режим>".
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
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()  # групповой чат поддержки (пусто = DM-фолбэк)
WEBHOOK_URL = "https://fixintel.ru/bot/webhook"
UPDATE_TYPES = ["message_created", "bot_started", "message_callback"]
RENEW_EVERY = float(os.environ.get("SUBSCRIPTION_RENEW_HOURS", "6")) * 3600  # авто-восстановление подписки
ADMIN_REPLY_TIMEOUT = float(os.environ.get("ADMIN_REPLY_TIMEOUT", "600"))  # ожидание ответа админа в группе

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
        cur.execute("""CREATE TABLE IF NOT EXISTS user_modes (
            max_user_id text PRIMARY KEY,
            mode text NOT NULL DEFAULT 'auto',
            updated_at timestamptz NOT NULL DEFAULT now())""")
        cn.commit()

# ---------- webhook-подписка: авто-восстановление (док: подписка периодически пропадает) ----------
async def renew_subscription():
    """Удалить все старые подписки бота и создать актуальную. Без ручного вмешательства."""
    headers = {"Authorization": BOT_TOKEN}
    async with httpx.AsyncClient(timeout=20) as c:
        try:
            r = await c.get(f"{MAX_API_BASE}/subscriptions", headers=headers)
            subs = r.json().get("subscriptions", []) if r.status_code == 200 else []
            for s in subs:
                await c.delete(f"{MAX_API_BASE}/subscriptions",
                               params={"url": s.get("url", "")}, headers=headers)
            body = {"url": WEBHOOK_URL, "update_types": UPDATE_TYPES, "secret": WEBHOOK_SECRET}
            r2 = await c.post(f"{MAX_API_BASE}/subscriptions", json=body, headers=headers)
            log.info("subscription renewed: %s", r2.text[:200])
        except Exception:
            log.exception("subscription renewal failed")

async def _renew_loop():
    while True:
        await asyncio.sleep(RENEW_EVERY)
        await renew_subscription()

# ---------- роли: переключатель Пользователь ПО / Админ поддержки (только для admin) ----------
MODES = {"auto", "user", "admin"}
MODE_CMD = {"режим", "mode", "/mode", "/режим"}

def get_mode(user_id: str) -> str:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT mode FROM user_modes WHERE max_user_id=%s", (user_id,))
        row = cur.fetchone()
    return row[0] if row else "auto"

def set_mode(user_id: str, mode: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO user_modes (max_user_id, mode, updated_at) VALUES (%s,%s,now()) "
                    "ON CONFLICT (max_user_id) DO UPDATE SET mode=EXCLUDED.mode, updated_at=now()",
                    (user_id, mode))
        cn.commit()

def mode_help(mode: str) -> str:
    return {
        "user":  "Режим 👤 ПОЛЬЗОВАТЕЛЯ ПО: вы видите бота как клиент (ответы из базы знаний, эскалация). Админ-команды отключены.",
        "admin": "Режим 🛠 АДМИНА ПОДДЕРЖКИ: ответ в обращение — #ТОКЕН текст; «обращения» — список; «статистика». Обычный диалог с ботом отключён.",
        "auto":  "Режим ⚙️ АВТО: обе роли одновременно — админ-команды перехватываются, всё остальное идёт как у клиента.",
    }[mode]

def mode_keyboard(current: str) -> list:
    def cb(label, mode):
        mark = "✅ " if current == mode else ""
        return {"type": "callback", "text": mark + label, "payload": "mode:" + mode}
    return [{
        "type": "inline_keyboard",
        "payload": {"buttons": [
            [cb("👤 Пользователь ПО", "user"), cb("🛠 Админ поддержки", "admin")],
            [cb("⚙️ Авто (обе роли)", "auto")],
        ]},
    }]

def is_active_admin(uid: str) -> bool:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (uid,))
        return cur.fetchone() is not None

async def max_send_chat(chat_id: str, text: str, attachments: list | None = None):
    payload = {"text": text[:4000], "random_id": random.randint(1, 2**31 - 1)}
    if attachments:
        payload["attachments"] = attachments
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{MAX_API_BASE}/messages",
                         params={"chat_id": chat_id}, json=payload,
                         headers={"Authorization": BOT_TOKEN})
        r.raise_for_status()

def ticket_keyboard(tid8: str) -> list:
    return [{"type": "inline_keyboard", "payload": {"buttons": [[
        {"type": "callback", "text": "✉️ Ответить", "payload": f"reply:{tid8}"},
        {"type": "callback", "text": "✅ Закрыть", "payload": f"close:{tid8}"},
    ]]}}]

async def notify_ticket(ticket_id, text: str):
    """Тикет в групповой чат поддержки (или админам в ЛС) с кнопками Ответить/Закрыть."""
    tid8 = str(ticket_id)[:8]
    kb = ticket_keyboard(tid8)
    if ADMIN_CHAT_ID:
        await max_send_chat(ADMIN_CHAT_ID, text, attachments=kb)
    else:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT max_user_id FROM bot_admins WHERE active")
            admins = [r[0] for r in cur.fetchall()]
        for a in admins:
            try:
                await max_send(a, text, attachments=kb)
            except Exception as e:
                log.warning("ticket notify failed %s: %s", a, e)

def panel_keyboard() -> list:
    return [{"type": "inline_keyboard", "payload": {"buttons": [
        [{"type": "callback", "text": "📥 Обращения", "payload": "panel:tickets"},
         {"type": "callback", "text": "📊 Статистика", "payload": "panel:stats"}],
        [{"type": "callback", "text": "🛠 Команды", "payload": "panel:help"}],
    ]}}]

def panel_content(section: str) -> str:
    if section == "tickets":
        rows = open_tickets()
        if not rows:
            return "📥 Открытых обращений нет ✓"
        lines = ["📥 Открытые обращения (ответ в ЛС боту: #ТОКЕН текст):"]
        for tid, club, subj, st in rows:
            lines.append(f"#{str(tid)[:8]} [{st}] {club}: {subj[:60]}")
        return NL.join(lines)
    if section == "stats":
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT count(*) FROM tickets WHERE status IN ('new','in_progress','waiting')")
            open_n = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM incidents")
            inc_n = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM kb_articles WHERE kb_miss=true") if False else None
            cur.execute("SELECT count(*) FROM tickets WHERE kb_miss=true")
            gap_n = cur.fetchone()[0]
        return (f"📊 Статистика:{NL}• открытые обращения: {open_n}{NL}"
                f"• грубых обращений (incidents): {inc_n}{NL}• пробелов базы знаний (kb_miss): {gap_n}")
    return ("🛠 Команды администратора:" + NL +
            "#ТОКЕН текст — ответ в обращение" + NL +
            "тикеты / обращения — список открытых" + NL +
            "статистика — грубые обращения по пользователям" + NL +
            "режим — переключатель роли (Пользователь/Админ/Авто)" + NL +
            "панель — эти вкладки")

# ---------- MAX ----------
async def max_send(user_id: str, text: str, attachments: list | None = None):
    # визуальный маркер режима: в админ-режиме каждое сообщение бота админу — с префиксом 🛠
    try:
        if get_mode(user_id) == "admin":
            text = "🛠 " + text[:3997]
    except Exception:
        pass
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
        r2 = await c.post(url, files={"data": (name, data, "image/png")})
        log.info("cdn resp[%s]: %s", r2.status_code, r2.text[:300])
        if r2.status_code >= 400:
            raise RuntimeError(f"cdn upload {r2.status_code}")
        if not token:
            try:
                d2 = r2.json()
                if isinstance(d2.get("photos"), dict):  # факт: {"photos": {"0": {"token": ...}}}
                    for v in d2["photos"].values():
                        if isinstance(v, dict) and v.get("token"):
                            token = v["token"]
                            break
                token = token or d2.get("token") or d2.get("photo") or d2.get("file")
            except Exception:
                pass
        if not token:
            raise RuntimeError("no token in uploads and cdn responses")
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
        cur.execute("SELECT to_char(now() AT TIME ZONE 'Europe/Moscow', 'DD.MM.YYYY, HH24:MI')")
        ts = cur.fetchone()[0]
        cn.commit()
    return tid, ts

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
PENDING_ADMIN_REPLY = {}  # admin_uid -> {"tid8": str, "t": ts} — «Ответить» нажато, ждём текст в группе

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
    tid, ts = create_ticket(user_id, club_id, text, kb_miss=True, staff=staff)
    add_message(tid, "in", text, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    tid8 = str(tid)[:8]
    await max_send(user_id, "Передал вопрос инженеру поддержки. Ответ придёт сюда." + NL +
                   f"🎫 Обращение #{tid8} зарегистрировано: {ts}.")
    await notify_ticket(tid, f"❓ Пробел знаний, клуб {club_id}{who}" + NL +
                        f"🎫 #{tid8} · {ts}" + NL + text[:220])

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
    tid, ts = create_ticket(user_id, club_id, summary, kb_miss=False, staff=staff)
    add_message(tid, "in", summary, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    tid8 = str(tid)[:8]
    await max_send(user_id, "Вопрос передал специалисту поддержки. Ответ придёт сюда." + NL +
                   f"🎫 Обращение #{tid8} зарегистрировано: {ts}.")
    await notify_ticket(tid, f"🆘 Запрос специалиста, клуб {club_id}{who}" + NL +
                        f"🎫 #{tid8} · {ts}" + NL + summary[:260])

async def user_message(user_id: str, text: str, payload: str = "", is_admin: bool = False):
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
        if is_admin:
            # многопользовательский режим владельца: KB-ответы БЕЗ привязки клуба,
            # тикеты помечаются club_id='internal'
            club_id = "internal"
            intent = classify(text)
            if intent == "greeting":
                await max_send(user_id, "Здравствуйте! Режим владельца: спрашивайте как пользователь ПО, "
                                        "отвечайте по обращениям командами #ТОКЕН.")
                return
            if intent == "escalate":
                await escalate_flow(user_id, club_id, text, "owner")
                return
            if intent == "frustrated":
                log_incident(user_id, club_id, text)
            await answer_or_forward(user_id, club_id, text, "owner")
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
async def _startup():
    init_schema()
    await renew_subscription()
    asyncio.create_task(_renew_loop())
    # постоянная панель-вкладки в группе поддержки (интерфейс всегда под рукой, без команд)
    if ADMIN_CHAT_ID:
        try:
            await max_send_chat(ADMIN_CHAT_ID, "Панель поддержки FitIntel Pro — вкладки всегда здесь. Обновить: «панель».")
            await max_send_chat(ADMIN_CHAT_ID, "Выберите раздел:", attachments=panel_keyboard())
        except Exception:
            log.exception("panel post to group failed")

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

    # нажатие inline-кнопки (dev.max.ru): callback и message — на одном уровне Update
    cb = data.get("callback") or data.get("callback_query") or {}
    if cb:
        cb_uid = str(((cb.get("user") or {}).get("user_id")) or user_id or "")
        cb_pl = str(cb.get("payload") or "")
        if not cb_uid or not is_active_admin(cb_uid):
            return {"ok": True}
        if cb_pl.startswith("mode:"):
            m = cb_pl.split(":", 1)[1].strip().lower()
            if m in MODES:
                set_mode(cb_uid, m)
                await max_send(cb_uid, mode_help(m), attachments=mode_keyboard(m))
        elif cb_pl.startswith("reply:"):
            tok = cb_pl.split(":", 1)[1].strip()
            PENDING_ADMIN_REPLY[cb_uid] = {"tid8": tok, "t": time.time()}
            aname = ((cb.get("user") or {}).get("name") or "Админ")
            if ADMIN_CHAT_ID:
                await max_send_chat(ADMIN_CHAT_ID, f"✉️ {aname}, жду ответ в #{tok} — напишите его сообщением в этот чат (10 минут). Отмена — «отмена».")
            else:
                await max_send(cb_uid, f"✉️ Жду ответ в #{tok} — напишите его следующим сообщением (10 минут).")
        elif cb_pl.startswith("close:"):
            tok = cb_pl.split(":", 1)[1].strip()
            with conn() as cn, cn.cursor() as cur:
                cur.execute("UPDATE tickets SET status='closed', updated_at=now() WHERE id::text LIKE %s "
                            "AND status IN ('new','in_progress','waiting') RETURNING user_max_id", (tok + "%",))
                row = cur.fetchone()
                cn.commit()
            if row:
                try:
                    await max_send(row[0], "Ваше обращение закрыто. Если вопрос остался — просто напишите снова.")
                except Exception:
                    pass
            await max_send_chat(ADMIN_CHAT_ID, f"✅ Обращение #{tok} закрыто") if ADMIN_CHAT_ID else await max_send(cb_uid, f"✅ Обращение #{tok} закрыто")
        elif cb_pl.startswith("panel:"):
            sec = cb_pl.split(":", 1)[1].strip()
            await max_send(cb_uid, panel_content(sec), attachments=panel_keyboard())
        return {"ok": True}

    # bot_started (dev.max.ru): user_id и payload — в КОРНЕ Update: {"user": {"user_id"}, "payload"}
    if update_type == "bot_started":
        bu = data.get("user") or {}
        user_id = str(bu.get("user_id") or user_id)
        if not user_id:
            return {"ok": True}
        if not payload:
            payload = str(data.get("payload") or "")
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
            _adm = cur.fetchone() is not None
        try:
            if payload:
                await user_message(user_id, "", payload, _adm)
            else:
                await max_send(user_id, "Здравствуйте! Поддержка FitIntel Pro. Задавайте вопрос — "
                                        "настройки, права, платежи, ошибки.")
        except Exception:
            log.exception("bot_started failed for %s", user_id)
        return {"ok": True}
    if not user_id:
        return {"ok": True}
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
        is_admin = cur.fetchone() is not None
    # групповой чат поддержки: только команды, никаких KB-ответов
    rchat = str((msg.get("recipient") or {}).get("chat_id") or "")
    if ADMIN_CHAT_ID and rchat == ADMIN_CHAT_ID:
        if is_admin and text:
            pend = PENDING_ADMIN_REPLY.get(user_id)
            low_g = text.strip().lower()
            if pend and time.time() - pend["t"] < ADMIN_REPLY_TIMEOUT:
                tok = pend["tid8"]
                PENDING_ADMIN_REPLY.pop(user_id, None)
                if low_g in {"отмена", "cancel", "отменить"}:
                    await max_send_chat(ADMIN_CHAT_ID, f"↩️ Ответ в #{tok} отменён")
                    return {"ok": True}
                with conn() as cn, cn.cursor() as cur:
                    cur.execute("SELECT id, user_max_id FROM tickets WHERE id::text LIKE %s "
                                "AND status IN ('new','in_progress','waiting') LIMIT 1", (tok + "%",))
                    row = cur.fetchone()
                if row:
                    ticket_id, client_uid = row
                    add_message(ticket_id, "out", text.strip(), author=user_id)
                    await max_send(client_uid, text.strip())
                    await max_send_chat(ADMIN_CHAT_ID, f"✓ Ответ в #{tok} отправлен клиенту")
                else:
                    await max_send_chat(ADMIN_CHAT_ID, f"⚠️ Обращение #{tok} уже закрыто")
                return {"ok": True}
            if low_g in {"панель", "panel", "/panel"}:
                await max_send_chat(ADMIN_CHAT_ID, "Панель поддержки — выберите раздел:", attachments=panel_keyboard())
                return {"ok": True}
            await admin_command(user_id, text)
        return {"ok": True}
    try:
        if not text and not payload:
            return {"ok": True}

        if is_admin and text.strip().lower() in {"панель", "panel", "/panel"}:
            await max_send(user_id, "Панель поддержки — выберите раздел:", attachments=panel_keyboard())
            return {"ok": True}

        mode = get_mode(user_id) if is_admin else "user"
        # переключатель роли — текстовая команда (кнопки выше)
        if is_admin and text.strip().lower() in MODE_CMD:
            await max_send(user_id, mode_help(mode), attachments=mode_keyboard(mode))
            return {"ok": True}
        # админ-команды: в режимах auto и admin; в режиме user отключены
        if is_admin and text and mode != "user":
            if await admin_command(user_id, text):
                return {"ok": True}
            if mode == "admin":
                await max_send(user_id, "Режим 🛠 АДМИНА: ответ в обращение — #ТОКЕН текст; «обращения» — список; "
                                        "«режим» — переключатель роли.")
                return {"ok": True}
        await user_message(user_id, text, payload, is_admin)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
