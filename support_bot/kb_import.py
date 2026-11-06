"""Импорт docs/kb/*.md -> kb_articles (файлы смонтированы read-only в /kb_source).
Запуск: python kb_import.py /kb_source
Формат статьи: '## Вопрос' -> 'Ключевые слова: ...' -> '**Ответ.** ...' -> '**Если не помогло**'.
Идемпотентно: upsert по (source_file, question).
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
SCR_RE = re.compile(r"(scr-[\w\-]+\.png)")

def parse_file(path):
    rel = os.path.relpath(path, SRC).replace("\", "/")
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
        ans = re.split(r"\*\*Если не помогло", ans)[0].strip()
        shots = sorted(set(SCR_RE.findall(body)))
        if ans:
            arts.append((title, keywords, ans, cat, shots, rel))
    return arts

def main():
    files = sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True))
    total = 0
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
        cn.commit()
    print(f"IMPORTED={total}")

if __name__ == "__main__":
    main()
