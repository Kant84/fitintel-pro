"""Импорт docs/kb/*.md -> kb_articles (v3.1): вариации запроса, новые темы, скриншоты.
Строки «Категория:» и «Вариации запроса:» НЕ попадают в текст ответа (только в поля).

Формат статьи v3:
    ## <вопрос>
    Категория: <код>
    Вариации запроса: <фраза>, <фраза>, ...   (в старых файлах — «Ключевые слова:»)
    <тело: причина -> шаги -> ожидание -> типичные ошибки>
    **Если не помогло:** ...
Пометки скриншотов: 📷/🖼 [SCR-<токен>: ...] — вырезаются в screenshots.

Запуск: python kb_import.py [reset]   (reset — очистить kb_articles перед импортом)
"""
import os, re, sys, glob
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
SRC = os.environ.get("KB_SOURCE_DIR", "/kb_source")

CAT = {
    "errors": "Ошибки",
    "errors-extra": "Ошибки",
    "desktop/install-login": "Desktop: установка и вход",
    "desktop": "Desktop (экраны)",
    "cash-fiscal": "Касса и фискализация",
    "payments": "Платежи",
    "payments-extra": "Платежи",
    "notifications": "Уведомления",
    "notifications-events": "Уведомления",
    "visits-access": "Входы и доступ",
    "visits-extra": "Входы и доступ",
    "clients-subs": "Клиенты и абонементы",
    "clients-extra": "Клиенты и абонементы",
    "schedule-services": "Расписание и услуги",
    "analytics-ai": "Аналитика и AI",
    "music-dj": "Музыка и DJ-плеер",
    "users-rbac": "Пользователи и роли",
    "roles-day": "Пользователи и роли",
    "faceid": "Face ID",
    "settings-help": "Настройки и помощь",
    "settings-detail": "Настройки и помощь",
    "server": "Сервер",
    "server-admin": "Сервер: администрирование",
    "server-api": "Сервер: API",
    "skud-hardware": "СКУД и оборудование",
    "hardware-extra": "СКУД и оборудование",
    "vending": "Магазин и вендинг",
    "max-miniapp": "Мини-приложение MAX",
    "processes": "Регламенты клуба",
    "forms-sale": "Desktop: формы и окна",
    "journals-logs": "Журналы и логи",
    "data-routines": "Данные: импорт и перенос",
}
SKIP = {"00-index.md", "KB_SCREENSHOT_LINKS.md", "ERRORS_AND_MAP_ADDENDUM.md"}
JUNK_TITLES = {"Тестовая отправка (подвкладка «Тест»)", "Открыть чат и ответить клиенту", "Через «Помощь → Чат с клиентами (MAX)»"}

ART_RE = re.compile(r"^## (.+)$", re.M)
KW_RE  = re.compile(r"^(?:Ключевые слова|Вариации запроса):\s*(.+)$", re.M)
META_RE  = re.compile(r"^Категория:\s*.+$\n?", re.M)
KWLINE_RE = re.compile(r"^(?:Вариации запроса|Ключевые слова):\s*.+$\n?", re.M)
SCR_RE = re.compile(r"(?i)\bscr-([a-z0-9]+(?:-[a-z0-9]+)+)\b")

ALIAS = {
    "pay-01": "fin-01",
    "cash-01": "fin-02",
    "cash-02": "fin-15",
    "cash-03": "fin-18-xreport",
    "cash-04": "fin-02",
    "desktop-01": "install-03-wizard-address",
    "desktop-02": "install-04-wizard-license",
    "desktop-03": "conn-01",
    "desktop-04": "conn-02-активированный профиль",
    "desktop-05": "set-01",
    "errors-01": "err-01-token-expired",
    "errors-02": "err-09-login-invalid",
    "vend-01": "магазин-01",
    "an-01": "ai-01",
    "visits-02": "visits-02-released",
    "visits-03": "visits-01",
    "skud-01": "rfid-01",
    "sett-01": "set-01",
    "rbac-01": "users-01",
    "install-01-setup": "install-03-wizard-address",
    "install-03-setup-server": "install-03-wizard-address",
    "install-04-setup-license": "install-04-wizard-license",
}

def extract_shots(text):
    shots = set()
    out_lines = []
    for ln in text.splitlines():
        toks = SCR_RE.findall(ln)
        if toks and ("🖼" in ln or "📷" in ln or "[" in ln or ".png" in ln.lower()
                     or ln.strip().lower().startswith(("скриншот", "screenshot"))):
            for t in toks:
                shots.add("scr-" + ALIAS.get(t.lower(), t.lower()) + ".png")
            continue
        out_lines.append(ln)
    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, sorted(shots)

def parse_file(path):
    rel = os.path.relpath(path, SRC).replace(chr(92), "/")
    stem = rel[:-3] if rel.endswith(".md") else rel
    cat = CAT.get(stem, CAT.get(stem.split("/")[0], stem))
    text = open(path, encoding="utf-8").read()
    matches = list(ART_RE.finditer(text))
    arts = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        body = text[m.end(): matches[i+1].start() if i+1 < len(matches) else len(text)]
        kw = KW_RE.search(body)
        keywords = kw.group(1).strip() if kw else ""
        ans = META_RE.sub("", body, count=1)
        ans = KWLINE_RE.sub("", ans, count=1)
        a = re.search(r"\*\*Ответ\.\*\*", ans)
        if a:
            ans = ans[a.end():]
        ans = re.split(r"\*\*Если не помогло", ans)[0]
        ans, shots = extract_shots(ans)
        if ans and title.strip() not in JUNK_TITLES:
            arts.append((title, keywords, ans, cat, shots, rel))
    return arts

def main():
    reset = "reset" in sys.argv[1:]
    files = sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True))
    total = with_shots = 0
    with psycopg.connect(DATABASE_URL) as cn, cn.cursor() as cur:
        if reset:
            cur.execute("TRUNCATE kb_articles")
            print("RESET=1")
        for f in files:
            if os.path.basename(f) in SKIP:
                continue
            for (q, k, a, c, s, src) in parse_file(f):
                cur.execute(
                    "INSERT INTO kb_articles (question, keywords, answer, category, screenshots, source_file, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,now()) "
                    "ON CONFLICT (source_file, question) DO UPDATE SET "
                    "keywords=EXCLUDED.keywords, answer=EXCLUDED.answer, category=EXCLUDED.category, "
                    "screenshots=EXCLUDED.screenshots, updated_at=now()",
                    (q, k, a, c, s, src))
                total += 1
                if s:
                    with_shots += 1
        cn.commit()
    print(f"IMPORTED={total} WITH_SHOTS={with_shots}")

if __name__ == "__main__":
    main()
