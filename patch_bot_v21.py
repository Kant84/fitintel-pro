# -*- coding: utf-8 -*-
# Патч support_bot/app.py -> v21 (fix: корректные переносы в команде «переимпорт»)
# 1) авто-переимпорт KB каждые KB_REIMPORT_HOURS + фоновая задача
# 2) команда админа «переимпорт»
# 3) GET /metrics
# Если прошлый запуск оставил app.py битым: git restore support_bot/app.py
import py_compile
PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()
changes = []

if "async def run_kb_import" in src:
    changes.append("kb-import: already present (skip)")
else:
    anchor = """async def _renew_loop():
    while True:
        await asyncio.sleep(RENEW_EVERY)
        await renew_subscription()"""
    assert src.count(anchor) == 1, "anchor _renew_loop не найден"
    body = """
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
        log.info("scheduled kb reimport: %s articles", n)"""
    src = src.replace(anchor, anchor + body, 1)
    changes.append("kb-import: inserted")

if "create_task(_kb_loop())" in src:
    changes.append("kb-loop: already present (skip)")
else:
    anchor = "    asyncio.create_task(_renew_loop())"
    assert src.count(anchor) == 1, "anchor create_task не найден"
    src = src.replace(anchor, anchor + "\n" + "    asyncio.create_task(_kb_loop())", 1)
    changes.append("kb-loop: started")

if "переимпорт" in src:
    changes.append("переимпорт-cmd: already present (skip)")
else:
    anchor = """async def admin_command(admin_id: str, text: str) -> bool:
    t = text.strip()
    low = t.lower()"""
    assert src.count(anchor) == 1, "anchor admin_command не найден"
    body = ("\n" + "    if low in {'переимпорт', 'reimport', 'обнови базу'}:" +
            "\n" + "        n = await run_kb_import()" +
            "\n" + "        await max_send(admin_id, f'База знаний обновлена: {n} статей' if n >= 0 else 'Ошибка импорта — смотрите логи')" +
            "\n" + "        return True")
    src = src.replace(anchor, anchor + body, 1)
    changes.append("переимпорт-cmd: inserted")

if "/metrics" in src:
    changes.append("metrics: already present (skip)")
else:
    anchor = """@app.get("/health")
def health():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        n = cur.fetchone()[0]
    return {"status": "ok", "kb_articles": n}"""
    assert src.count(anchor) == 1, "anchor /health не найден"
    body = ("\n" + """@app.get("/metrics")
def metrics():
    with conn() as cn, cn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_articles")
        kb = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tickets WHERE status IN ('new','in_progress','waiting')")
        open_t = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM incidents")
        inc = cur.fetchone()[0]
    return {"kb_articles": kb, "tickets_open": open_t, "incidents": inc}""")
    src = src.replace(anchor, anchor + body, 1)
    changes.append("metrics: inserted")

open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
for c in changes:
    print(c)
print("PATCH_OK=1")
