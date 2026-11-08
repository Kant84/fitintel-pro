# -*- coding: utf-8 -*-
# v27: has_domain нормализует запрос (опечатки проходят), пропускает FRUSTRATED,
# DOMAIN расширен при необходимости, kb_search: бонус за количество совпавших слов (ничьи).
import re, py_compile
PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()

NEW_HAS_DOMAIN = """def has_domain(text: str) -> bool:
    t = text.lower()
    if any(f in t for f in FRUSTRATED):
        return True
    try:
        t = normalize(text).lower()
    except Exception:
        pass
    return any(w in t for w in DOMAIN)
"""

NEW_DOMAIN = "DOMAIN = {\"клиент\",\"абонемент\",\"платёж\",\"платеж\",\"оплат\",\"касс\",\"ккт\",\"чек\",\"турникет\",\"браслет\",\"вход\",\"визит\",\"расписан\",\"услуг\",\"тренер\",\"пользовател\",\"роль\",\"прав\",\"лиценз\",\"desktop\",\"программ\",\"сервер\",\"настройк\",\"уведомлен\",\"email\",\"смс\",\"max\",\"вендинг\",\"автомат\",\"магазин\",\"склад\",\"зарплат\",\"отчёт\",\"отчет\",\"face\",\"музык\",\"шкафчик\",\"rfid\",\"скуд\",\"ошибк\",\"обновлен\",\"установк\",\"qr\",\"замер\",\"фискальн\",\"атол\",\"банк\",\"юкасса\",\"лог\",\"доступ\",\"парол\",\"баланс\",\"кошелёк\",\"бонус\",\"скидк\",\"замороз\",\"списан\",\"возврат\",\"продл\",\"тариф\",\"сообщен\",\"чат\",\"аналит\",\"kpi\",\"api\",\"синхрон\",\"бэкап\",\"резервн\",\"регистрац\",\"токен\",\"рассылк\",\"инструкц\",\"гид\",\"экспорт\",\"excel\",\"pdf\",\"1с\",\"интеграц\",\"лимит\",\"зал\",\"счётчик\",\"счетчик\",\"кто\",\"двойн\",\"индикатор\",\"сохранени\",\"подключен\",\"профил\",\"печать\",\"шаблон\"}"

NEW_SEARCH = """def kb_search(query: str):
    q = normalize(query)
    if not q:
        return None
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            "SELECT question, answer, screenshots, s + ("
            " SELECT count(*) FROM unnest(string_to_array(lower(%(q)s),' ')) w"
            " WHERE char_length(w) >= 4 AND (question ilike '%'||w||'%' OR coalesce(keywords,'') ilike '%'||w||'%')"
            ") * 0.05 AS total FROM ("
            " SELECT question, answer, screenshots,"
            "  (ts_rank(to_tsvector('russian', question), plainto_tsquery('russian', %(q)s)) * 2.0"
            "  + ts_rank(to_tsvector('russian', coalesce(keywords,'')), plainto_tsquery('russian', %(q)s)) * 1.5) * 10 AS s"
            " FROM kb_articles"
            " WHERE to_tsvector('russian', question || ' ' || coalesce(keywords,'')) @@ plainto_tsquery('russian', %(q)s)"
            " UNION ALL"
            " SELECT question, answer, screenshots,"
            "  GREATEST(similarity(question, %(raw)s), similarity(coalesce(keywords,''), %(raw)s))"
            " FROM kb_articles"
            " WHERE similarity(question, %(raw)s) >= 0.10 OR similarity(coalesce(keywords,''), %(raw)s) >= 0.10"
            " UNION ALL"
            " SELECT question, answer, screenshots,"
            "  (SELECT GREATEST(max(word_similarity(question, w)), max(word_similarity(coalesce(keywords,''), w)))"
            "   FROM unnest(string_to_array(lower(%(q)s),' ')) w WHERE char_length(w) >= 4) AS s"
            " FROM kb_articles"
            " WHERE EXISTS (SELECT 1 FROM unnest(string_to_array(lower(%(q)s),' ')) w"
            "               WHERE char_length(w) >= 4 AND (word_similarity(question, w) >= 0.25"
            "                    OR word_similarity(coalesce(keywords,''), w) >= 0.25))"
            ") t ORDER BY total DESC LIMIT 1",
            {"q": q, "raw": query})
        row = cur.fetchone()
        if row and float(row[3]) >= 0.10:
            return row[0], row[1], row[2], float(row[3])
    return None
"""

m = re.search(r"def has_domain\(.*?\):.*?(?=\ndef )", src, re.S)
assert m, "has_domain не найден"
src = src[:m.start()] + NEW_HAS_DOMAIN + "\n" + src[m.end():]
print("has_domain: replaced")

if "списан" not in src:
    src, c = re.subn(r"DOMAIN = \{.*?\}", lambda x: NEW_DOMAIN, src, count=1, flags=re.S)
    assert c == 1, "DOMAIN"
    print("DOMAIN: extended")
else:
    print("DOMAIN: ok")

assert len(re.findall(r"def kb_search\(query: str\):", src)) == 1
src = re.sub(r"def kb_search\(query: str\):.*?(?=\n(?:def |@app|# -{3,}))", lambda m2: NEW_SEARCH + "\n", src, count=1, flags=re.S)
print("kb_search: replaced (word-count bonus)")

open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("V27_PATCH_OK=1")
