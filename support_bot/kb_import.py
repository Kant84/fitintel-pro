"""Импорт docs/kb/*.md -> kb_articles (v2): понимает пометки скриншотов в тексте.

Форматы пометок в статьях (всё регистронезависимо):
    🖼 [SCR-pay-01: форма «Провести платёж»]
    Скриншот: scr-cash-01.png
Пометки вырезаются из текста ответа, превращаются в массив screenshots (scr-<токен>.png).
Запуск: python kb_import.py /kb_source   (идемпотентно: upsert по (source_file, question))
"""
import os, re, sys, glob
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
SRC = sys.argv[1] if len(sys.argv) > 1 else "/kb_source"

CAT = {
    "errors": "Ошибки",
    "desktop/install-login": "Desktop: установка и вход",
    "cash-fiscal": "Касса и фискализация",
    "payments": "Платежи",
    "notifications": "Уведомления",
    "visits-access": "Входы и доступ",
    "clients-subs": "Клиенты и абонементы",
    "schedule-services": "Расписание и услуги",
    "analytics-ai": "Аналитика и AI",
    "music-dj": "Музыка и DJ-плеер",
    "users-rbac": "Пользователи и роли",
    "faceid": "Face ID",
    "settings-help": "Настройки и помощь",
    "server": "Сервер",
    "skud-hardware": "СКУД и оборудование",
    "vending": "Магазин и вендинг",
}
SKIP = {"00-index.md", "KB_SCREENSHOT_LINKS.md"}
ART_RE = re.compile(r"^## (.+)$", re.M)
KW_RE  = re.compile(r"^Ключевые слова:\s*(.+)$", re.M)
# scr-<тема>-<NN> / SCR-pay-01 / scr-cash-01.png — регистронезависимо
SCR_RE = re.compile(r"(?i)\bscr-([a-z0-9]+(?:-[a-z0-9]+)+)\b")

# Токены в статьях -> реальные файлы docs/images/desktop (по SCREENSHOT_MAP.md).
# Дополняется по мере сверки статей; неуверенные mapping'и сюда НЕ добавлять.
# Сверено с реальным списком файлов в docs/images/desktop (Git, коммит 3e9b2929).
# Токен (без префикса scr-/SCR-) -> имя файла без "scr-" и ".png".
ALIAS = {
    "pay-01": "fin-01",                              # форма «Провести платёж"
    "cash-01": "fin-02",                             # касса ПКО/РКО
    "cash-02": "fin-15",                             # диалог «Настройки кассы (АТОЛ)"
    "cash-03": "fin-18-xreport",                     # X-отчёт
    "cash-04": "fin-02",
    "desktop-01": "install-03-wizard-address",       # мастер установки: адрес сервера
    "desktop-02": "install-04-wizard-license",       # мастер установки: лицензия
    "desktop-03": "conn-01",                         # параметры подключения
    "desktop-04": "conn-02-активированный профиль",  # активированный профиль
    "desktop-05": "set-01",                          # настройки-хаб
    "errors-01": "err-01-token-expired",
    "errors-02": "err-09-login-invalid",
    "vend-01": "магазин-01",                          # магазин (серверный склад)
    "an-01": "ai-01",                                # AI центр
    "visits-02": "visits-02-released",
    "visits-03": "visits-01",
    "skud-01": "rfid-01",                            # RFID Монитор
    "sett-01": "set-01",
    "rbac-01": "users-01",                           # список пользователей
}

def extract_shots(text):
    """Возвращает (очищенный_текст, [scr-xxx.png, ...]).
    Строка-пометка: содержит scr-токен И (эмодзи картинки ИЛИ '[' ИЛИ '.png' ИЛИ начинается со слова Скриншот)."""
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
        ans = body
        a = re.search(r"\*\*Ответ\.\*\*", body)
        if a:
            ans = body[a.end():]
        ans = re.split(r"\*\*Если не помогло", ans)[0]
        ans, shots = extract_shots(ans)
        if ans:
            arts.append((title, keywords, ans, cat, shots, rel))
    return arts

def main():
    files = sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True))
    total = with_shots = 0
    with psycopg.connect(DATABASE_URL) as cn, cn.cursor() as cur:
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
