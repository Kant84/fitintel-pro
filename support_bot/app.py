"""FitIntel Support Bot — v24: слияние ветвей (панель v6 + культурный формат/IDF v17).

База: версия с админ-панелью (panel:*, shift_marks, групповой чат, кнопки Ответить/Закрыть,
«Мои обращения», авто-продление подписки). Из v10–v17 перенесено: обращение по имени MAX,
компоновщик ответов (5 вариантов), интент «не помогло», off-topic отказ, IDF-поиск,
выгрузка «пробелы». Исправлен баг mark_shift (%s без параметров).
"""
import asyncio, json, logging, os, random, re, time, math, datetime
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
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()  # групповой чат поддержки (пусто = DM-фолбэк)
WEBHOOK_URL = "https://fixintel.ru/bot/webhook"
UPDATE_TYPES = ["message_created", "bot_started", "message_callback"]
RENEW_EVERY = float(os.environ.get("SUBSCRIPTION_RENEW_HOURS", "6")) * 3600  # авто-восстановление подписки
ADMIN_REPLY_TIMEOUT = float(os.environ.get("ADMIN_REPLY_TIMEOUT", "600"))  # ожидание ответа админа в группе

STOP = {"как","можно","подскажите","пожалуйста","помогите","помощь","здравствуйте",
        "здравствуй","добрый","доброе","день","вечер","утро","спасибо","заранее",
        "сделать","делать","надо","нужно","нужна","хочу","хочется","почему","зачем",
        "кто","что","где","когда","какой","какая","какие","чем","ли",
        "у","в","на","по","за","из","с","со","к","не","ни","же","бы","а","и","но","это","то",
        "без","может","могу","могут","мог","могла","после","перед","между","два","две","три",
        "дня","день","дней","неделю","месяц","год","сегодня","вчера","завтра","сейчас",
        "уже","ещё","еще","тоже","очень","вообще","просто","именно","почти","потом","сразу",
        "назад","тут","там","куда","откуда","свой","своя","свои","сам","сама","сами",
        "его","её","их","этот","эта","эти","один","одна","одни","какой-то","какая-то","я"}
GREETINGS = {"привет","здравствуйте","здравствуй","добрый","доброе","hello","hi","хай","хелло","салют"}
FRUSTRATED = {"гонишь","очумел","бред","чушь","хрень","ерунда","отстой","задолбал","исправьте","почините","ты что","вы что","алле","але","эй","слушай","что за","нифига","капец","бесит","уроды","тупой","тупая","кривой","это ещё что","возмутительно"}
ESCALATE = {"оператор","живой","живого","человек","специалист","админ","администратор","свяжите","свяжи","позовите","диспетчер","горячая линия","нужен человек","соедините","всё не работает","все не работает","ничего не работает","не работает вообще","полный сбой"}
NOT_HELPED = {"не помогло","не помог","не сработало","не сработал","не помогает",
              "по прежнему","по-прежнему","прежнему","всё ещё","все еще","всё еще",
              "опять","снова не","ничего не изменилось","не изменилось","так и есть",
              "не работает до сих пор","без изменений","не решило"}
URGENT = {"срочно","горит","критично","все стоит","всё стоит","клуб стоит","не пускает никого"}
OFFTOPIC_PHRASES = {"курс доллара","курс евро","курс валют","курс биткоина","цена биткоина",
    "сколько стоит доллар","сколько стоит евро","какая погода","погода на","прогноз погоды",
    "что приготовить","рецепт ","анекдот","гороскоп","во сколько матч","кто выиграл",
    "результат матча","познакомимся","новости дня","что случилось в мире","кто президент",
    "скачать фильм","ставки на","спорим","загадай число"}
OFFTOPIC_SINGLE = {"погода","доллар","евро","биткоин","матч","рецепт","анекдот","гороскоп","президент","валют"}
OFFTOPIC_REPLY = "Не нашёл готового ответа в базе знаний. Уточните, пожалуйста, какая именно функция или экран не работает (например: касса, турникет, Face ID, клиенты, отчёты) — передам вопрос инженеру поддержки."
# синонимы: формы запроса -> лексемы KB (OR-дополнение tsquery)
SYN = {"платеж":"оплат","платежи":"оплат","платёж":"оплат","оплат":"платеж",
       "оплата":"платеж","оплатить":"платеж","заплат":"платеж",
       "абонемент":"подписк","замороз":"заморозк","размороз":"заморозк",
       "турникет":"проход","проход":"турникет","вход":"проход","браслет":"проход",
       "касса":"ккт","ккт":"касса чек","чек":"ккт касса",
       "скидк":"бонус","бонус":"скидк","тренер":"услуг расписан",
       "вендинг":"автомат магазин","автомат":"вендинг магазин"}

LONG_ANSWER_LEN = 1800  # вариант 3 — объёмные ответы

def offtopic_hit(text: str) -> bool:
    t = " " + text.lower().strip() + " "
    if any(p in t for p in OFFTOPIC_PHRASES):
        return True
    singles = sum(1 for w in OFFTOPIC_SINGLE if w in t)
    return singles >= 2 and not any(f in t for f in FRUSTRATED)

DOMAIN = {"клиент","абонемент","платёж","платеж","оплат","касс","ккт","чек","турникет","браслет","вход","визит","расписан","услуг","тренер","пользовател","роль","прав","лиценз","desktop","программ","сервер","настройк","уведомлен","email","смс","max","вендинг","автомат","магазин","склад","зарплат","отчёт","отчет","face","музык","шкафчик","rfid","скуд","ошибк","обновлен","установк","qr","замер","фискальн","атол","банк","юкасса","лог","доступ","парол","баланс","кошелёк","бонус","скидк","замороз","списан","возврат","продл","тариф","сообщен","чат","аналит","kpi","api","синхрон","бэкап","резервн","регистрац","токен","рассылк","инструкц","гид","экспорт","excel","pdf","1с","интеграц","лимит","зал","счётчик","счетчик","кто","двойн","индикатор","сохранени","подключен","профил","печать","шаблон"}

def has_domain(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in DOMAIN)

def normalize(q: str) -> str:
    q = re.sub(r"[^\w\s-]", " ", q.lower(), flags=re.UNICODE)
    q = " ".join(q.split())
    for _b, _g in {"турнет": "турникет", "абонемант": "абонемент", "сдлать": "сделать",
                   "неработает": "не работает", "абонемен": "абонемент"}.items():
        q = re.sub(r"\b" + _b + r"\b", _g, q)
    return q


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
        cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sender_name text")
        cur.execute("""CREATE TABLE IF NOT EXISTS shift_marks (
            max_user_id text NOT NULL, day date NOT NULL, at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (max_user_id, day))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bot_settings (
            key text PRIMARY KEY, value text NOT NULL)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_modes (
            max_user_id text PRIMARY KEY,
            mode text NOT NULL DEFAULT 'auto',
            updated_at timestamptz NOT NULL DEFAULT now())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_names (
            max_user_id text PRIMARY KEY,
            name text NOT NULL)""")
        cn.commit()

# ---------- webhook-подписка: авто-восстановление ----------
async def renew_subscription():
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
KB_REIMPORT_EVERY = float(os.environ.get("KB_REIMPORT_HOURS", "6")) * 3600

async def run_kb_import() -> int:
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "kb_import.py", os.environ.get("KB_SOURCE_DIR", "/kb_source"),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        await proc.communicate()
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT count(*) FROM kb_articles")
            return cur.fetchone()[0]
    except Exception:
        log.exception("kb import failed")
        return -1

async def _kb_loop():
    while True:
        await asyncio.sleep(KB_REIMPORT_EVERY)
        n = await run_kb_import()
        log.info("scheduled kb reimport: %s articles", n)

# ---------- роли: переключатель Пользователь ПО / Админ поддержки ----------
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

def get_setting(key: str, default: str = "") -> str:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT value FROM bot_settings WHERE key=%s", (key,))
        row = cur.fetchone()
    return row[0] if row else default

def set_setting(key: str, value: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO bot_settings (key, value) VALUES (%s,%s) "
                    "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))
        cn.commit()

def month_start_date():
    try:
        d = int(get_setting("stats_month_start", "1") or "1")
    except ValueError:
        d = 1
    d = min(max(d, 1), 28)
    with conn() as cn, cn.cursor() as cur:
        cur.execute("""SELECT CASE WHEN extract(day FROM now())::int >= %s
            THEN date_trunc('month', now())::date + (%s - 1)
            ELSE (date_trunc('month', now()) - interval '1 month')::date + (%s - 1) END""", (d, d, d))
        return cur.fetchone()[0]

def get_role(uid: str) -> str:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT role FROM bot_admins WHERE max_user_id=%s AND active", (uid,))
        row = cur.fetchone()
    return row[0] if row else ""

def find_open_ticket(uid: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id FROM tickets WHERE user_max_id=%s AND status IN ('new','in_progress','waiting') "
                    "ORDER BY updated_at DESC LIMIT 1", (uid,))
        return cur.fetchone()

def client_keyboard() -> list:
    return [{"type": "inline_keyboard", "payload": {"buttons": [[
        {"type": "callback", "text": "📥 Мои обращения", "payload": "my:tickets"}]]}}]

def my_tickets_text(uid: str) -> str:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT id, to_char(created_at AT TIME ZONE 'Europe/Moscow','DD.MM.YYYY HH24:MI'), "
                    "subject, status, club_id FROM tickets WHERE user_max_id=%s ORDER BY created_at DESC LIMIT 10", (uid,))
        rows = cur.fetchall()
    if not rows:
        return "📥 У вас пока нет обращений"
    st_ru = {"new": "новое", "in_progress": "в работе", "waiting": "ожидает", "closed": "завершено"}
    lines = ["📥 Ваши обращения (ответ придёт сюда):"]
    for tid, ts, subj, st, club in rows:
        lines.append(f"#{str(tid)[:8]} · {ts} · клуб {club} · {st_ru.get(st, st)} · {subj[:44]}")
    return NL.join(lines)

def cb_chat_id(data: dict, cb: dict) -> str:
    m = cb.get("message") or data.get("message") or {}
    return str(((m.get("recipient") or {}).get("chat_id")) or "")

async def cb_reply(data: dict, cb: dict, uid: str, text: str, attachments: list | None = None):
    if ADMIN_CHAT_ID and cb_chat_id(data, cb) == ADMIN_CHAT_ID:
        await max_send_chat(ADMIN_CHAT_ID, text, attachments=attachments)
    else:
        await max_send(uid, text, attachments=attachments)

def mark_shift(uid: str):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO shift_marks (max_user_id, day, at) VALUES (%s, CURRENT_DATE, now()) "
                    "ON CONFLICT (max_user_id, day) DO NOTHING "
                    "RETURNING to_char(now() AT TIME ZONE 'Europe/Moscow', 'HH24:MI')", (uid,))
        row = cur.fetchone()
        cn.commit()
    return row[0] if row else None

def today_shift() -> list:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT max_user_id, to_char(at AT TIME ZONE 'Europe/Moscow', 'HH24:MI') "
                    "FROM shift_marks WHERE day = CURRENT_DATE ORDER BY at")
        return cur.fetchall()

def ticket_keyboard(tid8: str) -> list:
    return [{"type": "inline_keyboard", "payload": {"buttons": [[
        {"type": "callback", "text": "✉️ Ответить", "payload": f"reply:{tid8}"},
        {"type": "callback", "text": "✅ Закрыть", "payload": f"close:{tid8}"},
    ]]}}]

async def notify_ticket(ticket_id, text: str):
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
        [{"type": "callback", "text": "✅ Я на смене", "payload": "shift:on"},
         {"type": "callback", "text": "🕐 Кто на смене", "payload": "panel:shift"}],
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
            cur.execute("SELECT count(*) FROM tickets WHERE status='closed'")
            closed_n = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM tickets WHERE status='closed' AND updated_at::date = CURRENT_DATE")
            closed_day = cur.fetchone()[0]
            ms = month_start_date()
            cur.execute("SELECT count(*) FROM tickets WHERE status='closed' AND updated_at >= %s AND updated_at < %s + interval '1 month'", (ms, ms))
            closed_month = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM incidents")
            inc_n = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM tickets WHERE kb_miss=true")
            gap_n = cur.fetchone()[0]
            cur.execute("SELECT club_id, count(*) FROM tickets GROUP BY 1 ORDER BY 2 DESC")
            by_club = cur.fetchall()
            cur.execute("SELECT author, count(*) FROM ticket_messages WHERE direction='out' AND author IS NOT NULL AND author<>'' GROUP BY 1 ORDER BY 2 DESC")
            by_admin = cur.fetchall()
            cur.execute("SELECT max_user_id, count(DISTINCT day) FROM shift_marks WHERE day >= %s AND day < %s + interval '1 month' GROUP BY 1 ORDER BY 2 DESC", (ms, ms))
            shifts = cur.fetchall()
        lines = ["📊 Статистика:",
                 f"• открытые обращения: {open_n}",
                 f"• завершённые обращения: {closed_n} (за день {closed_day}, за месяц {closed_month})",
                 f"• грубых обращений: {inc_n}",
                 f"• пробелов базы знаний: {gap_n}",
                 "• по клубам:"] + [f"   {c}: {n}" for c, n in by_club]
        nm = lambda u: load_name(u) or u
        lines += ["• по администраторам (ответов):"] + [f"   {nm(a)}: {n}" for a, n in by_admin]
        lines += ["• смен за месяц:"] + [f"   {nm(u)}: {n}" for u, n in shifts]
        return NL.join(lines)
    if section == "shift":
        rows = today_shift()
        if not rows:
            return "🕐 Сегодня никто не отметился на смене"
        return "🕐 На смене сегодня:" + NL + NL.join(f"• {load_name(uid) or uid} — с {t}" for uid, t in rows)
    if section == "month":
        ms = month_start_date()
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT count(*) FROM tickets WHERE status='closed' AND updated_at >= %s AND updated_at < %s + interval '1 month'", (ms, ms))
            closed_month = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM tickets WHERE kb_miss AND created_at >= %s AND created_at < %s + interval '1 month'", (ms, ms))
            gaps = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM incidents WHERE created_at >= %s", (ms,))
            incs = cur.fetchone()[0]
            cur.execute("SELECT max_user_id, count(DISTINCT day) FROM shift_marks WHERE day >= %s AND day < %s + interval '1 month' GROUP BY 1 ORDER BY 2 DESC", (ms, ms))
            shifts = cur.fetchall()
        return (f"📅 Месяц (с {ms}): завершено обращений {closed_month}, пробелов знаний {gaps}, грубых {incs}."
                + NL + "Смены:" + NL + NL.join(f"• {u}: {n}" for u, n in shifts))
    return ("🛠 Команды администратора:" + NL +
            "#ТОКЕН текст — ответить на обращение (оно остаётся открытым)." + NL +
            "закрыть #ТОКЕН — завершить обращение (или кнопка «Закрыть»)." + NL +
            "тикеты / обращения — список открытых" + NL +
            "пробелы — выгрузка вопросов без ответа (CSV-файл)" + NL +
            "панель — эти вкладки")
# ---------- MAX ----------
def extract_display_name(*dicts) -> str:
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
    name = fresh.strip() or load_name(user_id)
    return f"{name}, привет! 😊" if name else "Здравствуйте! 😊"

async def max_send(user_id: str, text: str, attachments: list | None = None):
    try:
        if is_active_admin(user_id) and get_mode(user_id) == "admin":
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
                if isinstance(d2.get("photos"), dict):
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

async def max_upload_file(name: str, data: bytes, mime: str = "text/csv"):
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{MAX_API_BASE}/uploads", params={"type": "file"},
                         headers={"Authorization": BOT_TOKEN})
        r.raise_for_status()
        d = r.json()
        log.info("uploads(file) resp: %s", json.dumps(d, ensure_ascii=False)[:300])
        url = d["url"]
        token = d.get("token")
        for key in ("files", "photos"):
            if not token and isinstance(d.get(key), dict):
                for v in d[key].values():
                    if isinstance(v, dict) and v.get("token"):
                        token = v["token"]
                        break
            if token:
                break
        r2 = await c.post(url, files={"data": (name, data, mime)})
        if r2.status_code >= 400:
            raise RuntimeError(f"cdn upload {r2.status_code}")
        if not token:
            try:
                d2 = r2.json()
                for key in ("files", "photos"):
                    if isinstance(d2.get(key), dict):
                        for v in d2[key].values():
                            if isinstance(v, dict) and v.get("token"):
                                token = v["token"]
                                break
                    if token:
                        break
                token = token or d2.get("token") or d2.get("file")
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
        await asyncio.sleep(1)
        await max_send(user_id, "Скриншоты:", attachments=atts)

# ---------- platform ----------
async def check_license(key: str):
    if len(key) < 12:
        return False, ""
    # 1) ключ валиден по формату и подписи владельца?
    payload, verified = decode_license(key)
    if not payload or not verified:
        log.info("license rejected: bad format/signature")
        return False, ""
    # 2) не просрочен?
    try:
        if str(payload.get("exp", "")) < datetime.date.today().isoformat():
            log.info("license rejected: expired %s", payload.get("exp"))
            return False, ""
    except Exception:
        pass
    # 3) клуб уже известен платформе?
    headers = {"X-Client-CN": f"CN={PLATFORM_ADMIN_CN}"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{PLATFORM_API_URL}/platform/clubs", headers=headers)
            if r.status_code == 200:
                for cl in r.json().get("clubs", []):
                    pref = cl.get("license_key")
                    if pref and key.startswith(pref[:-3]):
                        slug = cl.get("slug")
                        r2 = await c.get(f"{PLATFORM_API_URL}/platform/clubs/{slug}/license", headers=headers)
                        if r2.status_code == 200:
                            return (r2.json().get("status") in ALLOWED_LICENSE_STATUSES), slug
                        return False, ""
    except Exception as e:
        log.warning("license lookup failed: %s", e)
    # 4) АВТОРЕГИСТРАЦИЯ: клуба нет в platform_db — бот регистрирует его сам
    slug = auto_register_club(key, payload)
    if slug:
        return True, slug
    return False, ""

# ---------- лицензии: декодирование, подпись, АВТОРЕГИСТРАЦИЯ клубов ----------
import base64 as _b64
from cryptography.hazmat.primitives import serialization as _ser
from cryptography.exceptions import InvalidSignature as _BadSig

LICENSE_PUBLIC_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEADfqtuPbGBzn8VyTP8qTdUjSjXMJk1PmJdrBBhmwStKo=
-----END PUBLIC KEY-----"""
PUB_KEY = _ser.load_pem_public_key(LICENSE_PUBLIC_PEM)  # Ed25519, НЕ секрет (есть в репо)
PLATFORM_DATABASE_URL = os.environ.get("PLATFORM_DATABASE_URL", "")

def decode_license(key: str):
    """FIPRO-<base64url(json)>.<sig> -> (payload, verified). Формат: License Studio."""
    try:
        token = key.replace("FIPRO-", "").strip()
        raw, sig = token.rsplit(".", 1)
        payload = json.loads(_b64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode())
    except Exception:
        return None, False
    try:
        PUB_KEY.verify(_b64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)), raw.encode())
        return payload, True
    except Exception:
        return payload, False

def platform_conn():
    return psycopg.connect(PLATFORM_DATABASE_URL)

def auto_register_club(key: str, payload: dict):
    """Первая привязка клуба: бот сам создаёт запись в platform_db. Без ручных INSERT."""
    if not PLATFORM_DATABASE_URL:
        return None
    club_name = str(payload.get("club") or payload.get("club_id") or "Новый клуб").strip()[:120]
    pref = key[:60]
    exp = str(payload.get("exp") or "")[:10] or None
    base_slug = re.sub(r"[^a-z0-9]+", "-", club_name.lower()).strip("-")[:24] or "club"
    try:
        with platform_conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT slug FROM clubs WHERE license_key=%s", (pref,))
            row = cur.fetchone()
            if row:
                return row[0]
            slug = base_slug
            for _ in range(10):
                cur.execute("SELECT 1 FROM clubs WHERE slug=%s", (slug,))
                if not cur.fetchone():
                    break
                slug = base_slug + "-" + re.sub(r"[^a-z0-9]", "", _b64.urlsafe_b64encode(os.urandom(3)).decode())[:4]
            cur.execute("INSERT INTO clubs (name, slug, api_token, license_key, license_expires_at, license_paid_until, is_active, created_at) "
                        "VALUES (%s,%s,gen_random_uuid()::text,%s,%s,%s,true,now())",
                        (club_name, slug, pref, exp, exp))
            cn.commit()
            log.info("club AUTO-REGISTERED: %s (slug %s)", club_name, slug)
            return slug
    except Exception as e:
        log.warning("auto_register_club failed: %s", e)
        return None

# ---------- KB: FTS с весами + IDF-переранкинг ----------
TSV = ("setweight(to_tsvector('russian', question), 'A') || "
       "setweight(to_tsvector('russian', coalesce(keywords,'')), 'B')")

def _stem_hit(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if len(a) < 4 or len(b) < 4:
        return a == b
    if a in b or b in a:
        return True
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n >= 4

def _tok_hits(qt: set, words: set, idf: dict) -> float:
    return sum(idf.get(t, 0.0) for t in qt if any(_stem_hit(t, w) for w in words))

W_RANK, W_TITLE, W_KEYWORDS = 0.4, 0.5, 0.35

def kb_search(query: str):
    q = normalize(query)
    if not q:
        return None
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            "SELECT question, answer, screenshots, s FROM ("
            " SELECT question, answer, screenshots,"
            "  (ts_rank(to_tsvector('russian', question), plainto_tsquery('russian', %(q)s)) * 2.0"
            "  + ts_rank(to_tsvector('russian', coalesce(keywords,'')), plainto_tsquery('russian', %(q)s)) * 1.5) * 10 AS s"
            " FROM kb_articles"
            " WHERE to_tsvector('russian', question || ' ' || coalesce(keywords,'')) @@ plainto_tsquery('russian', %(q)s)"
            " UNION ALL"
            " SELECT question, answer, screenshots,"
            "  GREATEST(similarity(question, %(raw)s), similarity(coalesce(keywords,''), %(raw)s))"
            " FROM kb_articles"
            " WHERE question %% %(raw)s OR coalesce(keywords,'') %% %(raw)s"
            " UNION ALL"
            " SELECT question, answer, screenshots,"
            "  (SELECT GREATEST(max(word_similarity(question, w)), max(word_similarity(coalesce(keywords,''), w)))"
            "   FROM unnest(string_to_array(lower(%(q)s),' ')) w WHERE char_length(w) >= 4) AS s"
            " FROM kb_articles"
            " WHERE EXISTS (SELECT 1 FROM unnest(string_to_array(lower(%(q)s),' ')) w"
            "               WHERE char_length(w) >= 4 AND (word_similarity(question, w) >= 0.25"
            "                    OR word_similarity(coalesce(keywords,''), w) >= 0.25))"
            ") t ORDER BY s DESC LIMIT 1",
            {"q": q, "raw": query})
        row = cur.fetchone()
        if row and float(row[3]) >= 0.10:
            return row[0], row[1], row[2], float(row[3])
    return None


# ---------- «культурный» компоновщик ответов ----------
def compose_answer(user_id: str, question: str, ans: str) -> str:
    g = greet(user_id)
    q = question.strip().strip("«»").rstrip(".")
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

# ---------- tickets / incidents ----------
def add_message(ticket_id, direction, body, author=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO ticket_messages (ticket_id, direction, body, author) VALUES (%s,%s,%s,%s)",
                    (ticket_id, direction, body, author))
        cur.execute("UPDATE tickets SET updated_at=now(), "
                    "status=CASE WHEN status='new' THEN 'in_progress' ELSE status END WHERE id=%s", (ticket_id,))
        cn.commit()

def create_ticket(user_id, club_id, text, kb_miss, staff="", sender_name=""):
    with conn() as cn, cn.cursor() as cur:
        cur.execute("INSERT INTO tickets (user_max_id, club_id, subject, status, kb_miss, sender_name) "
                    "VALUES (%s,%s,%s,'new',%s,%s) RETURNING id",
                    (user_id, club_id, text[:120], kb_miss, sender_name[:64] or None))
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
GAP_CMD = {"пробелы","выгрузка пробелов","kb_miss","пробелы знаний"}
CLOSE_RE = re.compile(r"^(?:закрыть|close|/close)\s+#?([0-9A-Za-z]{4,16})$")

async def _reply(admin_id: str, text: str, attachments: list | None = None):
    """Ответ на админ-команду: в групповой чат поддержки (если задан), иначе в DM."""
    if ADMIN_CHAT_ID:
        await max_send_chat(ADMIN_CHAT_ID, text, attachments=attachments)
    else:
        await _reply(admin_id, text, attachments=attachments)

async def close_ticket_by_token(tok: str, by_admin: str) -> str:
    with conn() as cn, cn.cursor() as cur:
        cur.execute("UPDATE tickets SET status='closed', updated_at=now() WHERE id::text LIKE %s "
                    "AND status IN ('new','in_progress','waiting') RETURNING user_max_id", (tok + "%",))
        row = cur.fetchone()
        cn.commit()
    if not row:
        return f"⚠️ Обращение #{tok} не найдено среди открытых"
    try:
        await max_send(row[0], f"{greet(row[0])}{NL}Ваше обращение закрыто. Если вопрос остался — просто напишите снова.")
    except Exception:
        pass
    return f"✅ Обращение #{tok} закрыто"

async def admin_command(admin_id: str, text: str) -> bool:
    t = text.strip()
    low = t.lower()
    if low in {'переимпорт', 'reimport', 'обнови базу'}:
        n = await run_kb_import()
        await max_send(admin_id, f'База знаний обновлена: {n} статей' if n >= 0 else 'Ошибка импорта — смотрите логи')
        return True
    mc = CLOSE_RE.match(low)
    if mc:
        res = await close_ticket_by_token(mc.group(1), admin_id)
        if ADMIN_CHAT_ID:
            await max_send_chat(ADMIN_CHAT_ID, res)
        else:
            await _reply(admin_id, res)
        return True
    if low in GAP_CMD:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT created_at, club_id, subject, status FROM tickets "
                        "WHERE kb_miss ORDER BY created_at DESC LIMIT 500")
            rows = cur.fetchall()
        if not rows:
            await _reply(admin_id, "Пробелов знаний нет — бот отвечает на все вопросы ✓")
            return True
        def csvq(s):
            s = str(s).replace('"', '""').replace("\n", " ").replace("\r", " ")
            return '"' + s + '"'
        lines = ["дата;клуб;вопрос;статус"]
        for created, club, subj, st in rows:
            lines.append(";".join([created.strftime("%Y-%m-%d %H:%M"),
                                   csvq(club), csvq(subj), csvq(st)]))
        data = ("\ufeff" + NL.join(lines)).encode("utf-8")
        try:
            token = await max_upload_file("kb_gaps.csv", data)
            await _reply(admin_id,
                f"Выгрузка пробелов знаний: {len(rows)} вопросов. Колонки: дата;клуб;вопрос;статус.",
                attachments=[{"type": "file",
                              "payload": {"token": token, "filename": "kb_gaps.csv"}}])
        except Exception as e:
            log.warning("kb_gaps upload failed: %s", e)
            lines = [f"Пробелов знаний: {len(rows)}. Файл не отправился — вот список:"]
            for i, (created, club, subj, st) in enumerate(rows[:30], 1):
                lines.append(f"{i}. [{club}] {subj}")
            await _reply(admin_id, NL.join(lines)[:3900])
        return True
    if low in STAT_CMD:
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT user_max_id, club_id, count(*) FROM incidents "
                        "GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            await _reply(admin_id, "Грубых обращений не зафиксировано ✓")
            return True
        lines = ["Статистика грубых обращений (по пользователям):"]
        for uid, club, n in rows:
            lines.append(f"{load_name(uid) or uid} (клуб {club}): {n}")
        await _reply(admin_id, NL.join(lines))
        return True
    if low in LIST_CMD:
        rows = open_tickets()
        if not rows:
            await _reply(admin_id, "Открытых обращений нет ✓")
            return True
        lines = ["Открытые обращения (ответ: #ТОКЕН текст):"]
        for tid, club, subj, st in rows:
            lines.append(f"#{str(tid)[:8]} [{st}] {club}: {subj[:60]}")
        await _reply(admin_id, NL.join(lines))
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
        await _reply(admin_id, f"Обращение #{tok} не найдено среди открытых. Команда «обращения» — список.")
        return True
    ticket_id, user_id = row
    add_message(ticket_id, "out", body, author=admin_id)
    await max_send(user_id, body)
    await _reply(admin_id, f"✓ Ответ ушёл в обращение #{str(ticket_id)[:8]} (открыто — закрыть: «закрыть #{str(ticket_id)[:8]}»)")
    return True

# ---------- flows ----------
PENDING_ESCALATE = {}   # user_id -> {"t","attempts","orig","extra","club","staff"}
PENDING_ADMIN_REPLY = {}  # admin_id -> {"t", "ticket_id"}

NOT_HELPED_INTRO = ("Жаль, что не помогло 🙁 Соединяю со специалистом — скажите, пожалуйста: на каком шаге "
                    "инструкции вы остановились и что именно увидели (текст ошибки, скриншот)?")

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

async def answer_or_forward(user_id: str, club_id: str, text: str, staff: str = "", sname: str = ""):
    if offtopic_hit(text):
        log.info("offtopic refused: %.80s", text)
        await max_send(user_id, f"{greet(user_id)}{NL}{OFFTOPIC_REPLY}")
        return
    if not has_domain(text):
        log.info("no-domain refused: %.80s", text)
        await max_send(user_id, f"{greet(user_id)}{NL}{OFFTOPIC_REPLY}")
        return
    hit = kb_search(text)
    if hit:
        q, ans, shots, score = hit
        log.info("kb hit (%.3f): %s", score, q[:80])
        await max_send(user_id, compose_answer(user_id, q, ans))
        await max_send_screenshots(user_id, list(shots or []))
        return
    tid, ts = create_ticket(user_id, club_id, text, kb_miss=True, staff=staff, sender_name=sname)
    add_message(tid, "in", text, author=user_id)
    who = f" · сотрудник {sname or staff}" if (sname or staff) else ""
    urgent = "СРОЧНО: " if any(w in text.lower() for w in URGENT) else ""
    await max_send(user_id, f"{greet(user_id)} 🙂{NL}По этому вопросу у меня пока нет готового ответа — "
                            "передал его инженеру поддержки, ответ придёт сюда. Если ситуация критична "
                            "(касса, доступ), добавьте в сообщение «СРОЧНО».",
               attachments=client_keyboard())
    await notify_ticket(tid, f"{urgent}❓ Пробел знаний, клуб {club_id}{who}:{NL}"
                             f"«{text[:400]}»{NL}Клиент: {sname or user_id} · {ts}{NL}"
                             f"Ответить: #ТОКЕН текст")

async def escalate_flow(user_id: str, club_id: str, text: str, staff: str = "",
                        intro: str | None = None, sname: str = ""):
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
    tid, ts = create_ticket(user_id, club_id, summary, kb_miss=False, staff=staff, sender_name=sname)
    add_message(tid, "in", summary, author=user_id)
    who = f" · сотрудник {sname or staff}" if (sname or staff) else ""
    await max_send(user_id, f"{greet(user_id)}{NL}Передал специалисту поддержки с вашими деталями. Ответ придёт сюда.",
               attachments=client_keyboard())
    await notify_ticket(tid, f"🆘 Запрос специалиста, клуб {club_id}{who}:{NL}"
                             f"«{summary[:400]}»{NL}Клиент: {sname or user_id} · {ts}{NL}"
                             f"Ответить: #ТОКЕН текст")

async def user_message(user_id: str, text: str, payload: str = "", is_admin: bool = False, sname: str = ""):
    staff = ""
    if payload and "~" in payload:
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
            club_id = "internal"
            intent = classify(text)
            if intent == "greeting":
                await max_send(user_id, f"{greet(user_id, sname)}{NL}Режим владельца: спрашивайте как пользователь ПО, "
                                        "отвечайте по обращениям командами #ТОКЕН.")
                return
            if intent == "not_helped":
                await escalate_flow(user_id, club_id, text, "owner", NOT_HELPED_INTRO, sname)
                return
            if intent == "escalate":
                await escalate_flow(user_id, club_id, text, "owner", sname=sname)
                return
            if intent == "frustrated":
                log_incident(user_id, club_id, text)
            await answer_or_forward(user_id, club_id, text, "owner", sname)
            return
        await max_send(user_id, "Здравствуйте! Это поддержка FitIntel Pro. Откройте чат кнопкой «Поддержка "
                                "разработчика» в desktop-клиенте — клуб подключится автоматически, и можно "
                                "сразу писать вопрос.")
        return

    club_id = bound[0]
    if text.strip().lower() in {"мои обращения", "мои тикеты", "мои заявки"}:
        await max_send(user_id, my_tickets_text(user_id), attachments=client_keyboard())
        return
    intent = classify(text)
    if intent == "greeting":
        await max_send(user_id, f"{greet(user_id, sname)}{NL}Задавайте вопрос — настройки, права, платежи, ошибки.",
                       attachments=client_keyboard())
        return
    if intent == "not_helped":
        await escalate_flow(user_id, club_id, text, staff, NOT_HELPED_INTRO, sname)
        return
    if intent == "escalate":
        await escalate_flow(user_id, club_id, text, staff, sname=sname)
        return
    if intent == "frustrated":
        log_incident(user_id, club_id, text)
        await max_send(user_id, f"{greet(user_id, sname)}{NL}Понимаю, ситуация неприятная. Опишите парой фраз: какой экран, "
                                "что делали, что получилось в итоге — сразу поищу решение.")
    await answer_or_forward(user_id, club_id, text, staff, sname)

# ---------- http ----------
app = FastAPI(title="FitIntel Support Bot")

@app.on_event("startup")
async def _startup():
    init_schema()
    asyncio.create_task(_renew_loop())
    asyncio.create_task(_kb_loop())

@app.get("/health")
def health():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        n = cur.fetchone()[0]
    return {"status": "ok", "kb_articles": n}
@app.get("/metrics")
def metrics():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        kb = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tickets WHERE status IN ('new','in_progress','waiting')")
        open_t = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM incidents")
        inc = cur.fetchone()[0]
    return {"kb_articles": kb, "tickets_open": open_t, "incidents": inc}

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
    sname = (sender.get("name") or "").strip() or ((sender.get("first_name") or "") + " " + (sender.get("last_name") or "")).strip()

    if user_id and sname:
        try:
            save_name(user_id, sname)
        except Exception:
            pass

    # нажатие inline-кнопки
    cb = data.get("callback") or data.get("callback_query") or {}
    if cb:
        cb_uid = str(((cb.get("user") or {}).get("user_id")) or user_id or "")
        cb_pl = str(cb.get("payload") or "")
        sname_cb = (cb.get("user") or {}).get("name") or ""
        if cb_uid and sname_cb:
            try:
                save_name(cb_uid, sname_cb)
            except Exception:
                pass
        if cb_uid and cb_pl == "my:tickets":
            await cb_reply(data, cb, cb_uid, my_tickets_text(cb_uid))
            return {"ok": True}
        if cb_uid and cb_pl.startswith("mode:"):
            if is_active_admin(cb_uid):
                m = cb_pl.split(":", 1)[1].strip().lower()
                if m in MODES:
                    set_mode(cb_uid, m)
                    await max_send(cb_uid, mode_help(m), attachments=mode_keyboard(m))
            return {"ok": True}
        if cb_uid and cb_pl.startswith("reply:"):
            if is_active_admin(cb_uid):
                tok = cb_pl.split(":", 1)[1]
                with conn() as cn, cn.cursor() as cur:
                    cur.execute("SELECT id FROM tickets WHERE id::text LIKE %s LIMIT 1", (tok + "%",))
                    row = cur.fetchone()
                if row:
                    PENDING_ADMIN_REPLY[cb_uid] = {"t": time.time(), "ticket_id": row[0]}
                    await cb_reply(data, cb, cb_uid,
                                   f"✉️ Режим ответа на #{tok}. Пришлите текст — уйдёт клиенту. "
                                   f"Выход: «отмена» или любая команда #ТОКЕН.")
            return {"ok": True}
        if cb_uid and cb_pl.startswith("close:"):
            if is_active_admin(cb_uid):
                res = await close_ticket_by_token(cb_pl.split(":", 1)[1], cb_uid)
                await cb_reply(data, cb, cb_uid, res)
            return {"ok": True}
        if cb_uid and cb_pl == "shift:on":
            first = mark_shift(cb_uid)
            if first:
                await cb_reply(data, cb, cb_uid,
                               f"✅ Вы отметились на смене в {first} (МСК). Хорошего дежурства!")
                if ADMIN_CHAT_ID:
                    try:
                        await max_send_chat(ADMIN_CHAT_ID, f"👋 Админ {cb_uid} на смене с {first}")
                    except Exception:
                        pass
            else:
                await cb_reply(data, cb, cb_uid, "Вы уже отмечены на смене сегодня ✓")
            return {"ok": True}
        if cb_uid and cb_pl.startswith("panel:"):
            if is_active_admin(cb_uid):
                sec = cb_pl.split(":", 1)[1]
                first_mark = mark_shift(cb_uid)
                await cb_reply(data, cb, cb_uid, panel_content(sec))
            return {"ok": True}
        return {"ok": True}

    # bot_started
    if update_type == "bot_started":
        bu = data.get("user") or {}
        user_id = str(bu.get("user_id") or user_id)
        if not user_id:
            return {"ok": True}
        if not payload:
            payload = str(data.get("payload") or "")
        if (bu.get("name") or "").strip():
            try:
                save_name(user_id, bu.get("name"))
            except Exception:
                pass
        with conn() as cn, cn.cursor() as cur:
            cur.execute("SELECT 1 FROM bot_admins WHERE max_user_id=%s AND active", (user_id,))
            _adm = cur.fetchone() is not None
        try:
            if payload:
                await user_message(user_id, "", payload, _adm, (bu.get("name") or "").strip())
            else:
                await max_send(user_id, f"{greet(user_id)}{NL}Поддержка FitIntel Pro. Задавайте вопрос — "
                                        "настройки, права, платежи, ошибки.")
        except Exception:
            log.exception("bot_started failed for %s", user_id)
        return {"ok": True}

    # групповой чат поддержки: ответы админов -> в тикет; «панель»/«месяц»
    if (ADMIN_CHAT_ID and update_type == "message_created"
            and str(msg.get("chat_id") or (msg.get("recipient") or {}).get("chat_id") or "") == ADMIN_CHAT_ID):
        if not user_id or sender.get("is_bot"):
            return {"ok": True}
        if is_active_admin(user_id):
            if text.strip().lower() == "панель":
                await max_send_chat(ADMIN_CHAT_ID, "Панель поддержки FitIntel Pro — вкладки всегда здесь. Обновить: «панель».",
                                    attachments=panel_keyboard())
                return {"ok": True}
            if text.strip().lower() in {"период"}:
                await max_send_chat(ADMIN_CHAT_ID, panel_content("month"))
                return {"ok": True}
            if text.strip().lower().startswith("месяц"):
                parts = text.split()
                if len(parts) == 1:
                    await max_send_chat(ADMIN_CHAT_ID, f"Начало расчётного месяца: {get_setting('stats_month_start', '1')}-е число. Сменить (владелец): «месяц 5».")
                    return {"ok": True}
                if get_role(user_id) == "superadmin" and parts[1].isdigit() and 1 <= int(parts[1]) <= 28:
                    set_setting("stats_month_start", parts[1])
                    await max_send_chat(ADMIN_CHAT_ID, f"✅ Расчётный месяц начинается {parts[1]}-го числа.")
                else:
                    await max_send_chat(ADMIN_CHAT_ID, "Не изменено: нужна роль владельца и число 1–28.")
                return {"ok": True}
            if text:
                first = mark_shift(user_id)
                p = PENDING_ADMIN_REPLY.get(user_id)
                if p and time.time() - p["t"] < ADMIN_REPLY_TIMEOUT:
                    PENDING_ADMIN_REPLY.pop(user_id, None)
                    with conn() as cn, cn.cursor() as cur:
                        cur.execute("SELECT user_max_id FROM tickets WHERE id=%s AND status IN ('new','in_progress','waiting')", (p["ticket_id"],))
                        row = cur.fetchone()
                    if row:
                        add_message(p["ticket_id"], "out", text, author=user_id)
                        await max_send(row[0], text)
                        await max_send_chat(ADMIN_CHAT_ID, f"✓ Ответ в #{str(p['ticket_id'])[:8]} ушёл клиенту")
                        return {"ok": True}
                handled = await admin_command(user_id, text)
                if handled:
                    return {"ok": True}
                await max_send_chat(ADMIN_CHAT_ID, "Не распознал команду. Команды: «панель», «тикеты», «пробелы», «закрыть #ТОКЕН», ответ — #ТОКЕН текст (или кнопка «Ответить»).")
                return {"ok": True}
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
        if is_admin and text.strip().lower() in MODE_CMD:
            await max_send(user_id, mode_help(mode), attachments=mode_keyboard(mode))
            return {"ok": True}
        if is_admin and text and mode != "user":
            low_t = text.strip().lower()
            if (low_t in LIST_CMD or low_t in STAT_CMD or low_t in GAP_CMD
                    or low_t == "панель" or low_t in {"месяц"} or CLOSE_RE.match(low_t)
                    or ADMIN_REPLY_RE.match(text)):
                await max_send(user_id, f"{greet(user_id)}{NL}Это админ-команда — она работает в групповом чате "
                                        "поддержки (там же панель с кнопками). Здесь клиентский режим: задавайте "
                                        "вопросы по работе ПО.", attachments=client_keyboard())
                return {"ok": True}
            if mode == "admin":
                await max_send(user_id, f"{greet(user_id)}{NL}Режим 🛠 АДМИНА доступен в групповом чате поддержки. "
                                        "Здесь клиентский режим: задавайте вопросы по работе ПО.",
                               attachments=client_keyboard())
                return {"ok": True}
        await user_message(user_id, text, payload, is_admin, sname)
    except Exception:
        log.exception("handle failed for %s", user_id)
    return {"ok": True}
