# -*- coding: utf-8 -*-
# Патч support_bot/app.py -> v25 (поиск, финальный):
# normalize со словарём опечаток; kb_search: FTS + fuzzy + word-level ВСЕГДА, лучший результат, порог 0.10.
import re, py_compile
PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()

NEW_NORM = """def normalize(q: str) -> str:
    q = re.sub(r"[^\\w\\s-]", " ", q.lower(), flags=re.UNICODE)
    q = " ".join(q.split())
    for _b, _g in {"турнет": "турникет", "абонемант": "абонемент", "сдлать": "сделать",
                   "неработает": "не работает", "абонемен": "абонемент"}.items():
        q = re.sub(r"\\b" + _b + r"\\b", _g, q)
    return q
"""

NEW_SEARCH = """def kb_search(query: str):
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
"""

assert len(re.findall(r"def normalize\(q: str\) -> str:", src)) == 1, "normalize not found"
assert len(re.findall(r"def kb_search\(query: str\):", src)) == 1, "kb_search not found"
src = re.sub(r"def normalize\(q: str\) -> str:.*?(?=\ndef )", lambda m: NEW_NORM + "\n", src, count=1, flags=re.S)
src = re.sub(r"def kb_search\(query: str\):.*?(?=\n(?:def |@app|# -{3,}))", lambda m: NEW_SEARCH + "\n", src, count=1, flags=re.S)
print("normalize+kb_search: replaced")

anchor2 = "    return singles >= 2"
if anchor2 in src and "not any(f in t for f in FRUSTRATED)" not in src:
    src = src.replace(anchor2, "    return singles >= 2 and not any(f in t for f in FRUSTRATED)", 1)
    print("offtopic-vs-frustrated: fixed")
else:
    print("offtopic-vs-frustrated: skip (already or anchor missing)")

open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("V25_PATCH_OK=1")
