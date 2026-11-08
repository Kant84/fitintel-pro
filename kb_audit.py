# -*- coding: utf-8 -*-
"""Аудит docs/kb: правила качества + поиск мусора. Запуск: python kb_audit.py docs/kb
Проверяет КАЖДУЮ статью всех .md: структура, ключевые слова, длина, тематика ПО,
мусорные маркеры, дубли вопросов, битые скриншоты. Отчёт + список на удаление.
"""
import os, re, sys, glob, json

SRC = sys.argv[1] if len(sys.argv) > 1 else "docs/kb"
SHOTS_DIR = "docs/images/desktop"

DOMAIN = {"клиент","абонемент","платёж","платеж","оплат","касс","ккт","чек","турникет","браслет",
          "вход","визит","расписан","услуг","тренер","пользовател","роль","прав","лиценз","desktop",
          "программ","сервер","настройк","уведомлен","email","смс","max","вендинг","автомат","магазин",
          "склад","зарплат","отчёт","отчет","face","музык","шкафчик","rfid","скуд","ошибк","обновлен",
          "установк","qr","замер","фискальн","атол","эквайринг","банк","юкасса","скриншот","лог","доступ",
          "парол","баланс","кошелёк","бонус","скидк","замороз","списан","возврат","продл","тариф",
          "сообщен","чат","карточк","анкет","документ","фото","камер","токен","api","синхрон","резервн",
          "бэкап","оборудован","считыват","пропуск","онлайн","офлайн"}
JUNK_Q = re.compile(r"(?i)тестовая|(^|[^а-я])тест([^а-я]|$)|открыть чат и ответить|как написать в макс|"
                    r"max сообщения →|проверка связи с ботом|нашли чат по этой ссылке")
JUNK_ANSWER = re.compile(r"(?i)max сообщения → чаты|vk|telegram|мессенджер max|скачать приложение max")
ART_RE = re.compile(r"^## (.+)$", re.M)

shot_files = set()
if os.path.isdir(SHOTS_DIR):
    shot_files = set(os.listdir(SHOTS_DIR))

report, questions_seen = [], {}
stats = {"files": 0, "articles": 0, "ok": 0}

for path in sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True)):
    base = os.path.basename(path)
    if base in {"00-index.md", "KB_SCREENSHOT_LINKS.md"}:
        continue
    stats["files"] += 1
    text = open(path, encoding="utf-8").read()
    ms = list(ART_RE.finditer(text))
    for i, m in enumerate(ms):
        q = m.group(1).strip()
        body = text[m.end(): ms[i+1].start() if i+1 < len(ms) else len(text)]
        stats["articles"] += 1
        problems = []
        if "Ключевые слова:" not in body:
            problems.append("нет ключевых слов")
        if "**Ответ.**" not in body:
            problems.append("нет Ответа")
        ans = body.split("**Ответ.**", 1)[-1].split("**Если не помогло")[0]
        lines = [l for l in ans.splitlines() if l.strip()]
        if len(lines) < 8:
            problems.append(f"короткий ответ ({len(lines)} строк)")
        low = (q + " " + body).lower()
        if not any(w in low for w in DOMAIN):
            problems.append("нет тематики ПО")
        if JUNK_Q.search(q) or JUNK_ANSWER.search(body):
            problems.append("МУСОР")
        for shot in re.findall(r"scr-[\w\-]+\.png", body):
            if shot not in shot_files:
                problems.append(f"битый скрин {shot}")
        key = q.lower()
        if key in questions_seen:
            problems.append(f"дубль ({questions_seen[key]})")
        else:
            questions_seen[key] = path
        if problems:
            report.append({"file": os.path.relpath(path, SRC), "question": q[:90], "problems": problems})
        else:
            stats["ok"] += 1

print(f"Файлов: {stats['files']} | Статей: {stats['articles']} | Чистых: {stats['ok']} | С проблемами: {len(report)}")
junk = [r for r in report if "МУСОР" in r["problems"]]
print(f"Мусорных статей: {len(junk)}")
for r in report:
    mark = " [МУСОР]" if "МУСОР" in r["problems"] else ""
    print(f"- {r['file']} :: {r['question']}{mark} :: {', '.join(r['problems'])}")

with open("kb_audit_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
with open("kb_junk_delete.sql", "w", encoding="utf-8") as f:
    f.write("-- Удаление мусорных статей (проверьте список выше перед выполнением!)\n")
    for r in junk:
        q = r["question"].replace("'", "''")
        f.write(f"DELETE FROM kb_articles WHERE source_file='{r['file'].replace(chr(92),'/')}' AND question='{q}';\n")
print("Файлы: kb_audit_report.json, kb_junk_delete.sql")
print("AUDIT_OK=1")
