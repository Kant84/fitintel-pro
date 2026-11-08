import re, py_compile
PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()

NEW_NORM = """def normalize(q: str) -> str:
    q = re.sub(r"[^\\w\\s-]", " ", q.lower(), flags=re.UNICODE)
    return " ".join(q.split())
"""

NEW_SEARCH = """def kb_search(query: str):
    q = normalize(query)
    if not q:
        return None
    with conn() as cn, cn.cursor() as cur:
        cur.execute(
            "SELECT question, answer, screenshots, "
            "ts_rank(to_tsvector('russian', question), plainto_tsquery('russian', %s)) * 2.0 + "
            "ts_rank(to_tsvector('russian', coalesce(keywords,'')), plainto_tsquery('russian', %s)) * 1.5 "
            "FROM kb_articles "
            "WHERE to_tsvector('russian', question || ' ' || coalesce(keywords,'')) @@ plainto_tsquery('russian', %s) "
            "ORDER BY 4 DESC LIMIT 1", (q, q, q))
        row = cur.fetchone()
        if row and float(row[3]) >= 0.01:
            return row[0], row[1], row[2], float(row[3])
        cur.execute(
            "SELECT question, answer, screenshots, "
            "GREATEST(similarity(question, %s), similarity(coalesce(keywords,''), %s)) "
            "FROM kb_articles WHERE question %% %s OR coalesce(keywords,'') %% %s ORDER BY 4 DESC LIMIT 1",
            (query, query, query, query))
        row = cur.fetchone()
        if row and float(row[3]) >= 0.15:
            return row[0], row[1], row[2], float(row[3])
    return None
"""

assert len(re.findall(r"def normalize\(q: str\) -> str:", src)) == 1
assert len(re.findall(r"def kb_search\(query: str\):", src)) == 1
src = re.sub(r"def normalize\(q: str\) -> str:.*?(?=\ndef )", lambda m: NEW_NORM + "\n", src, count=1, flags=re.S)
src = re.sub(r"def kb_search\(query: str\):.*?(?=\n(?:def |@app|# -{3,}))", lambda m: NEW_SEARCH + "\n", src, count=1, flags=re.S)
open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("SEARCH_PATCH_OK=1")
