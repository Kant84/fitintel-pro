"""FitIntel Support Bot — v13: «культурный» формат ответов + сценарии поддержки.

Ответы клиенту (регламент формата, 07.11.2026):
- Обращение по ИМЕНИ из профиля MAX (первой строкой): «<Имя>, привет! 😊»
- Простые вопросы — вариант 1 (суть + предложение подробностей)
- Инструкции — вариант 2 (шаги + одна типовая ошибка + предложение помощи)
- Объёмные (>1800 знаков) — вариант 3 (сначала «Коротко», потом детали)
- Плохие новости — вариант 4 (честно + рабочие альтернативы)
- Нужны детали — вариант 5 (один конкретный нюанс, 30 секунд)
- Запрещено: канцелярит, «извините, нельзя» без альтернатив, суть в середине.
- Эскалационный футер добавляется к каждому KB-ответу (в статьях «Если не помогло»
  обрезано импортёром — добавляем централизованно).

Прочие регламенты (с v6–v9):
- Клиент НИКОГДА не видит слова «тикет». Нет ответа -> «Передал вопрос инженеру поддержки».
- Просьба специалиста / «не помогло»: до 2 уточняющих вопросов, затем передача с деталями.
- Грубые обращения -> таблица incidents, команда «статистика».
- Промахи KB -> tickets.kb_miss=true (база пробелов знаний).
- Поиск KB: FTS с весами (заголовок A, ключи/вариации B) + word_similarity fallback
  по заголовку+ключам; пороги через KB_MIN_RANK / KB_MIN_SIM; лог rank топ-1/2.
- Привязка клуба: deeplink ?start=<префикс ключа>[~login сотрудника] из desktop / ключ текстом.
- Админ: '#ТОКЕН текст' -> в обращение, 'тикеты'/'обращения' -> список, 'режим' -> переключатель
  роли (👤 Пользователь ПО / 🛠 Админ поддержки / ⚙️ Авто). Эха нет.
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
PLATFORM_ADMIN_CN = os.environ.get("PLATFORM_ADMIN_CN", "andrei@fitintel.ru")
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
        "у","в","на","по","за","из","с","со","к","не","ни","же","бы","а","и","но","это","то",
        "без","может","могу","могут","мог","могла","после","перед","между","два","две","три",
        "дня","день","дней","неделю","месяц","год","сегодня","вчера","завтра","сейчас",
        "уже","ещё","еще","тоже","очень","вообще","просто","именно","почти","потом","сразу",
        "назад","тут","там","куда","откуда","свой","своя","свои","сам","сама","сами",
        "его","её","их","этот","эта","эти","один","одна","одни","какой-то","какая-то"}
GREETINGS = {"привет","здравствуйте","здравствуй","добрый","доброе","hello","hi","хай","хелло","салют"}
FRUSTRATED = {"гонишь","очумел","бред","чушь","хрень","ерунда","отстой","задолбал",
              "исправьте","почините","ты что","вы что","алле","але","эй","слушай",
              "что за","нифига","капец","бесит","уроды","тупой","тупая","кривой"}
ESCALATE = {"оператор","живой","живого","человек","специалист","админ","администратор",
            "свяжите","свяжи","позовите","диспетчер","горячая линия","поддержку позови",
            "нужен человек","соедините"}
NOT_HELPED = {"не помогло","не помог","не сработало","не сработал","не помогает",
              "по прежнему","по-прежнему","прежнему","всё ещё","все еще","всё еще",
              "опять","снова не","ничего не изменилось","не изменилось","так и есть",
              "не работает до сих пор","без изменений","не решило"}
URGENT = {"срочно","горит","критично","все стоит","всё стоит","клуб стоит","не пускает никого"}
# синонимы: формы запроса -> лексемы KB (OR-дополнение tsquery)
SYN = {"платеж":"оплат","платежи":"оплат","платёж":"оплат","оплат":"платеж",
       "оплата":"платеж","оплатить":"платеж","заплат":"платеж",
       "абонемент":"подписк","замороз":"заморозк","размороз":"заморозк",
       "турникет":"проход","проход":"турникет","вход":"проход","браслет":"проход",
       "касса":"ккт","ккт":"касса чек","чек":"ккт касса",
       "скидк":"бонус","бонус":"скидк","тренер":"услуг расписан",
       "вендинг":"автомат магазин","автомат":"вендинг магазин"}

LONG_ANSWER_LEN = 1800  # вариант 3 — объёмные ответы

# ---------- имена пользователей MAX ----------
def extract_display_name(*dicts) -> str:
    """Имя из полей webhook MAX: sender/name/first_name+last_name."""
    for d in dicts:
        if not isinstance(d, dict):
            continue
        n = (d.get("name") or "").strip()
        if n:
            return n
        fn = (d.get("first_name") or "").strip()
        ln = (d.get("last_name") or "").strip()
        if fn or ln:
            return (fn + " " + ln).strip()
    return ""

def save_name(user_id: str, name: str):
    name = name.strip()[:80]
    if not name:
        return
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO user_names (max_user_id, name) VALUES (%s,%s) "
                    "ON CONFLICT (max_user_id) DO UPDATE SET name=EXCLUDED.name",
                    (user_id, name))
        cn.commit()

def load_name(user_id: str) -> str:
    try:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT name FROM user_names WHERE max_user_id=%s", (user_id,))
            row = cur.fetchone()
        return row[0] if row else ""
    except Exception:
        return ""

def greet(user_id: str, fresh: str = "") -> str:
    """Вариант-1 обращение: по имени из MAX (иначе нейтральное)."""
    name = fresh.strip() or load_name(user_id)
    return f"{name}, привет! 😊" if name else "Здравствуйте! 😊"

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
    if any(a in t for a in NOT_HELPED):
        return "not_helped"
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
        cur.execute("""CREATE TABLE IF NOT EXISTS user_names (
            max_user_id text PRIMARY KEY,
            name text NOT NULL)""")
        cn.commit()

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

# ---------- KB: FTS с весами (заголовок A, ключи/вариации B) + word_similarity fallback ----------
TSV = ("setweight(to_tsvector('russian', question), 'A') || "
       "setweight(to_tsvector('russian', coalesce(keywords,'')), 'B')")

def _stem_hit(a: str, b: str) -> bool:
    """Стем-сравнение русских слов: общий префикс >=4 символов или вхождение."""
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n >= 4

import math

def _tok_hits(qt: set, words: set, idf: dict) -> float:
    return sum(idf.get(t, 0.0) for t in qt if any(_stem_hit(t, w) for w in words))

W_RANK, W_TITLE, W_KEYWORDS = 0.4, 0.5, 0.35

def kb_search(query: str):
    q = normalize(query)
    if not q:
        return None
    tsq = to_tsquery(q)
    qt = set(q.split())
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        N = max(cur.fetchone()[0], 1)
        # IDF: редкие слова запроса («восстановить») важнее частотных («клиент», «удалить»)
        idf = {}
        for t in qt:
            cur.execute(f"SELECT count(*) FROM kb_articles WHERE {TSV} @@ to_tsquery('russian', %s)", (t,))
            df = max(cur.fetchone()[0], 1)
            idf[t] = min(math.log(N / df + 1.0), 4.5)  # потолок: служебные редкие слова не доминируют
        # normalization=1: делим на 1+log(длина документа) — убираем перекос в пользу коротких
        cur.execute(
            f"SELECT question, answer, screenshots, category, keywords, "
            f"ts_rank({TSV}, to_tsquery('russian', %s), 1) AS rank "
            f"FROM kb_articles WHERE {TSV} @@ to_tsquery('russian', %s) "
            "ORDER BY rank DESC LIMIT 8", (tsq, tsq))
        rows = cur.fetchall()
        if rows:
            scored = []
            for question, answer, shots, cat, kws, rank in rows:
                tw = set(normalize(question).split())
                kw = set(normalize(kws or "").split())
                composite = (W_RANK * float(rank)
                             + W_TITLE * _tok_hits(qt, tw, idf)
                             + W_KEYWORDS * _tok_hits(qt, kw, idf))
                scored.append((composite, question, answer, shots, cat, float(rank)))
            scored.sort(key=lambda r: r[0], reverse=True)
            top = scored[0]
            second = scored[1] if len(scored) > 1 else None
            log.info("kb rank: winner=%.4f(fts %.4f) second=%s | idf=%s",
                     top[0], top[5],
                     ("%.4f(fts %.4f)" % (second[0], second[5])) if second else "-",
                     {t: round(v, 2) for t, v in sorted(idf.items(), key=lambda x: -x[1])})
            if top[5] >= KB_MIN_RANK:
                return top[1], top[2], top[3], top[4], top[0]
        cur.execute(
            "SELECT question, answer, screenshots, category, "
            "word_similarity(question || ' ' || coalesce(keywords,''), %s) AS sim "
            "FROM kb_articles WHERE question || ' ' || coalesce(keywords,'') %% %s "
            "ORDER BY sim DESC LIMIT 1", (query, query))
        row = cur.fetchone()
        if row and float(row[4]) >= SIM_MIN:
            return row[0], row[1], row[2], row[3], float(row[4])
    return None

# ---------- «культурный» компоновщик ответов ----------
def compose_answer(user_id: str, question: str, ans: str) -> str:
    """Вариант 2 (шаги) для обычных, вариант 3 (коротко+детали) для объёмных."""
    g = greet(user_id)
    q = question.strip().rstrip(".")
    if len(ans) > LONG_ANSWER_LEN:
        if "**Пошагово.**" in ans:
            short, rest = ans.split("**Пошагово.**", 1)
            short = short.replace("**Причина.**", "**Коротко.**").strip()
            details = "**Пошагово.**" + rest.strip()
        else:
            parts = ans.split("\n\n", 1)
            short = "**Коротко.** " + (parts[0][:400].strip())
            details = parts[1].strip() if len(parts) > 1 else ""
        return (f"{g} 👋{NL}Тут информации чуть больше — сначала суть, потом детали.{NL}{NL}"
                f"{short}{NL}{NL}{details}{NL}{NL}"
                "Если сейчас нужен только один аспект (только причина или только шаги) — скажите, дам без лишнего.\n"
                "Если не помогло — напишите «не помогло» и уточните, на каком шаге остановились (текст ошибки или скриншот). Передам инженеру.")
    return (f"{g}{NL}Вот как решается: «{q}» — по шагам, чтобы ничего не упустить:{NL}{NL}{ans}{NL}{NL}"
            "Если какой-то шаг непонятен — скажите, разберу на примере.\n"
            "Если не помогло — напишите «не помогло» и уточните, на каком шаге остановились (текст ошибки или скриншот). Передам инженеру.")

def compose_bad_news(user_id: str, limitation: str, alternatives: list[str]) -> str:
    """Вариант 4: честно об ограничении + рабочие альтернативы."""
    g = greet(user_id)
    alts = NL.join(f"{i+1}. {a}" for i, a in enumerate(alternatives))
    return (f"{g[:-2]} 😔{NL}К сожалению, тут есть ограничение: {limitation}{NL}"
            f"Но есть рабочие пути:{NL}{alts}")

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
    await max_send(user_id, f"{greet(user_id)}{NL}Клуб подключён. Задавайте вопрос — настройки, права, "
                            "платежи, ошибки. Отвечаю по базе знаний; если решения нет — передам вопрос инженеру.")
    return True

async def answer_or_forward(user_id: str, club_id: str, text: str, staff: str = ""):
    """KB-ответ (культурный формат); при промахе — переадресация инженеру (вариант 4 по тону)."""
    hit = kb_search(text)
    if hit:
        q, ans, shots, _cat, score = hit
        log.info("kb hit (%.3f): %s", score, q[:80])
        await max_send(user_id, compose_answer(user_id, q, ans))
        await max_send_screenshots(user_id, list(shots or []))
        return
    tid = create_ticket(user_id, club_id, text, kb_miss=True, staff=staff)
    add_message(tid, "in", text, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    urgent = "СРОЧНО: " if any(w in text.lower() for w in URGENT) else ""
    await max_send(user_id, f"{greet(user_id)} 🙂{NL}По этому вопросу у меня пока нет готового ответа — "
                            "передал его инженеру поддержки, ответ придёт сюда. Если ситуация критична "
                            "(касса, доступ), добавьте в сообщение «СРОЧНО».")
    await notify_admins(f"{urgent}❓ Пробел знаний, клуб {club_id}{who}: {text[:180]}" + NL +
                        f"Ответить: #{str(tid)[:8]} <текст>")

async def escalate_flow(user_id: str, club_id: str, text: str, staff: str = "",
                        intro: str | None = None):
    """Вариант 5: нужен один нюанс; до 2 уточнений, затем передача с деталями."""
    st = PENDING_ESCALATE.get(user_id)
    if not st or time.time() - st["t"] > ESCALATE_TIMEOUT:
        PENDING_ESCALATE[user_id] = {"t": time.time(), "attempts": 0, "orig": text, "extra": [],
                                     "club": club_id, "staff": staff}
        if intro:
            await max_send(user_id, intro)
        else:
            await max_send(user_id, f"{greet(user_id)} 🙂{NL}Соединяю со специалистом. Чтобы ответ был точным, "
                                    "нужен один нюанс: какой раздел/экран затронут и что именно происходит? "
                                    "Это займёт 30 секунд — зато ответ сразу по делу.")
        return
    st["t"] = time.time()
    st["attempts"] += 1
    if text.strip():
        st["extra"].append(text.strip())
    if st["attempts"] < 2 and len(text.strip()) < 15:
        await max_send(user_id, "Принял. Ещё одна деталь: текст ошибки или момент, когда это началось? (можно коротко)")
        return
    summary = st["orig"]
    if st["extra"]:
        summary += " | Уточнения: " + "; ".join(st["extra"])
    PENDING_ESCALATE.pop(user_id, None)
    tid = create_ticket(user_id, club_id, summary, kb_miss=False, staff=staff)
    add_message(tid, "in", summary, author=user_id)
    who = f" (сотрудник {staff})" if staff else ""
    await max_send(user_id, f"{greet(user_id)}{NL}Передал специалисту поддержки с вашими деталями. Ответ придёт сюда.")
    await notify_admins(f"🆘 Запрос специалиста, клуб {club_id}{who}: {summary[:220]}" + NL +
                        f"Ответить: #{str(tid)[:8]} <текст>")

NOT_HELPED_INTRO = ("Жаль, что не помогло 🙁 Соединяю со специалистом — скажите, пожалуйста: на каком шаге "
                    "инструкции вы остановились и что именно увидели (текст ошибки, скриншот)?")

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
            await max_send(user_id, compose_bad_news(user_id, "клуб по этой ссылке не опознан или лицензия не активна.",
                        ["Откройте чат кнопкой «Поддержка разработчика» в desktop-клиенте — клуб подключится автоматически.",
                         "Напишите нам напрямую: support@fixintel.ru (укажите название клуба)."]))
            return
        if text.strip().startswith("FIPRO-"):
            if await bind_club(user_id, text, "text"):
                return
            await max_send(user_id, compose_bad_news(user_id, "ключ не распознан или лицензия не активна.",
                        ["Проверьте, что ключ скопирован целиком (начинается с FIPRO-).",
                         "Если ключ верный, а лицензия просрочена — вопросы по продлению: support@fixintel.ru."]))
            return
        if is_admin:
            # многопользовательский режим владельца: KB-ответы БЕЗ привязки клуба,
            # тикеты помечаются club_id='internal'
            club_id = "internal"
            intent = classify(text)
            if intent == "greeting":
                await max_send(user_id, f"{greet(user_id)}{NL}Режим владельца: спрашивайте как пользователь ПО, "
                                        "отвечайте по обращениям командами #ТОКЕН.")
                return
            if intent == "not_helped":
                await escalate_flow(user_id, club_id, text, "owner", NOT_HELPED_INTRO)
                return
            if intent == "escalate":
                await escalate_flow(user_id, club_id, text, "owner")
                return
            if intent == "frustrated":
                log_incident(user_id, club_id, text)
            await answer_or_forward(user_id, club_id, text, "owner")
            return
        await max_send(user_id, compose_bad_news(user_id, "я пока не знаю, из какого вы клуба, а без этого не могу проверить лицензию.",
                    ["Откройте этот чат кнопкой «Поддержка разработчика» в desktop-клиенте (меню «Помощь») — клуб подключится автоматически.",
                     "Или напишите нам: support@fixintel.ru (укажите название клуба)."]))
        return

    club_id = bound[0]
    intent = classify(text)
    if intent == "greeting":
        await max_send(user_id, f"{greet(user_id)}{NL}Задавайте вопрос — настройки, права, платежи, ошибки.")
        return
    if intent == "not_helped":
        await escalate_flow(user_id, club_id, text, staff, NOT_HELPED_INTRO)
        return
    if intent == "escalate":
        await escalate_flow(user_id, club_id, text, staff)
        return
    if intent == "frustrated":
        log_incident(user_id, club_id, text)
        await max_send(user_id, f"{greet(user_id)}{NL}Понимаю, ситуация неприятная. Опишите парой фраз: какой экран, "
                                "что делали, что получилось в итоге — сразу поищу решение.")
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

    # имя пользователя MAX: из webhook -> кэш в БД (для обращений по имени)
    fresh_name = extract_display_name(sender, msg, body)
    if user_id and fresh_name:
        try:
            save_name(user_id, fresh_name)
        except Exception:
            pass

    # нажатие inline-кнопки (dev.max.ru): callback и message — на одном уровне Update
    cb = data.get("callback") or data.get("callback_query") or {}
    if cb:
        cb_uid = str(((cb.get("user") or {}).get("user_id")) or user_id or "")
        cb_pl = str(cb.get("payload") or "")
        if cb_uid and cb_pl.startswith("mode:"):
            with conn() as cn, cn.cursor() as cur:
                cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (cb_uid,))
                cb_admin = cur.fetchone() is not None
            if cb_admin:
                m = cb_pl.split(":", 1)[1].strip().lower()
                if m in MODES:
                    set_mode(cb_uid, m)
                    await max_send(cb_uid, mode_help(m), attachments=mode_keyboard(m))
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
                await max_send(user_id, f"{greet(user_id)}{NL}Поддержка FitIntel Pro. Задавайте вопрос — "
                                        "настройки, права, платежи, ошибки.")
        except Exception:
            log.exception("bot_started failed for %s", user_id)
        return {"ok": True}
    if not user_id:
        return {"ok": True}
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
        is_admin = cur.fetchone() is not None
    try:
        if not text and not payload:
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
