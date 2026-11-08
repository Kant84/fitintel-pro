# -*- coding: utf-8 -*-
'''Патч support_bot/kb_import.py (v3.1): мусор-фильтр на импорте. Запуск: python patch_import_v6b.py'''
import py_compile, re as _re
NL = chr(10)
PATH = "support_bot/kb_import.py"
src = open(PATH, encoding="utf-8").read()
if "JUNK_Q_RE" in src:
    print("guard: already present (skip)")
else:
    anchor = 'SKIP = {"00-index.md", "KB_SCREENSHOT_LINKS.md", "TROUBLESHOOTING.md"}'
    assert src.count(anchor) == 1, "anchor SKIP не найден (импортёр менялся)"
    rx = '(?i)тестовая|(^|[^а-я])тест([^а-я]|$)|открыть чат и ответить|как написать в макс|max сообщения|проверка связи с ботом|нашли чат по этой ссылке|запустить бота'
    addition = anchor + NL + "JUNK_Q_RE = _re.compile(rx)"
    src = src.replace(anchor, addition, 1)
    anchor2 = "        if ans:"
    assert src.count(anchor2) == 1, "anchor parse-loop не найден"
    src = src.replace(anchor2, "        if ans and not JUNK_Q_RE.search(title):", 1)
    open(PATH, "w", encoding="utf-8", newline="\n").write(src)
    print("guard: inserted")
py_compile.compile(PATH, doraise=True)
print("PATCH_IMPORT_OK=1")