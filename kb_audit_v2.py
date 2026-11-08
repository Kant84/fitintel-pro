# -*- coding: utf-8 -*-
"""Аудит v2 docs/kb: оба формата статей (параллельный: Категория/Вариации/Ответ-по-endpoint; классический: Ключевые слова/Ответ).
Запуск: python kb_audit_v2.py docs/kb  ->  экран (utf-8) + kb_audit_report.json + kb_junk_delete.sql"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import os, re, glob, json

SRC = sys.argv[1] if len(sys.argv) > 1 else "docs/kb"
SHOTS_DIR = "docs/images/desktop"

DOMAIN = {"клиент","абонемент","плат","касс","ккт","чек","турникет","браслет","вход","визит","расписан","услуг","тренер","пользовател","роль","прав","лиценз","программ","сервер","настройк","уведомлен","email","смс","вендинг","автомат","магазин","склад","зарплат","отчёт","отчет","face","музык","шкафчик","rfid","скуд","ошибк","обновлен","установк","qr","замер","фискальн","атол","банк","юкасса","лог","доступ","парол","баланс","кошелёк","бонус","скидк","замороз","возврат","продл","тариф","сообщен","чат","аналит","kpi","api","синхрон","бэкап","резервн","регистрац","токен","рассылк","инструкц","гид"}
JUNK_Q = re.compile(r"(?i)тестовая|(^|[^а-я])тест([^а-я]|$)|открыть чат и ответить|как написать в макс|max сообщения\s*→|проверка связи с ботом|нашли чат по этой ссылке|запустить бота|скачать приложение")
JUNK_ANSWER = re.compile(r"(?i)max сообщения\s*→|скачать приложение max|перейти в чат|найти чат в поиске")
ART_RE = re.compile(r"^## (.+)$", re.M)
KW_ANY = ("Ключевые слова:", "Вариации запроса:")

shot_files = set(os.listdir(SHOTS_DIR)) if os.path.isdir(SHOTS_DIR) else set()
report, seen, stats = [], {}, {"articles": 0, "ok": 0}

for path in sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True)):
    if os.path.basename(path) in {"00-index.md", "KB_SCREENSHOT_LINKS.md"}:
        continue
    text = open(path, encoding="utf-8").read()
    ms = list(ART_RE.finditer(text))
    for i, m in enumerate(ms):
        q = m.group(1).strip()
        body = text[m.end(): ms[i+1].start() if i+1 < len(ms) else len(text)]
        stats["articles"] += 1
        problems = []
        if not any(k in body for k in KW_ANY):
            problems.append("нет ключевых слов/вариаций")
        STRUCT = ("**Ответ", "**Причина", "**Пошагово", "**Типовые", "**Как открыть", "**Решение")
        if not any(m in body for m in STRUCT):
            problems.append("нет структуры ответа")
        if len(body.strip()) < 300 and "**Пошагово" not in body:
            problems.append("слишком короткая")
        low = (q + " " + body).lower()
        if not any(w in low for w in DOMAIN):
            problems.append("нет тематики ПО")
        if JUNK_Q.search(q) or JUNK_ANSWER.search(body):
            problems.append("МУСОР")
        for shot in re.findall(r"scr-[\w\-]+\.png", body):
            if shot not in shot_files:
                problems.append("битый скрин " + shot)
        key = q.lower()
        if key in seen:
            problems.append("дубль: " + seen[key])
        else:
            seen[key] = os.path.relpath(path, SRC)
        if problems:
            report.append({"file": os.path.relpath(path, SRC), "question": q[:90], "problems": problems})
        else:
            stats["ok"] += 1

junk = [r for r in report if "МУСОР" in r["problems"]]
print(f"Статей: {stats['articles']} | Чистых: {stats['ok']} | С проблемами: {len(report)} | Мусор: {len(junk)}")
for r in report:
    mark = " [МУСОР]" if "МУСОР" in r["problems"] else ""
    print("- " + r["file"] + " :: " + r["question"] + mark + " :: " + ", ".join(r["problems"]))
with open("kb_audit_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
with open("kb_junk_delete.sql", "w", encoding="utf-8") as f:
    f.write("-- Мусорные статьи (сверьте с экраном!)" + chr(10))
    for r in junk:
        qq = r["question"].replace("'", "''")
        ff = r["file"].replace(chr(92), "/")
        f.write(f"DELETE FROM kb_articles WHERE source_file='{ff}' AND question='{qq}';" + chr(10))
print("AUDIT_V2_OK=1")