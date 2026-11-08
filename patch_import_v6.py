# -*- coding: utf-8 -*-
"""Патч support_bot/kb_import.py: фильтр мусора на импорте (JUNK-статьи не попадут в БД).
Запуск из корня репозитория:  python patch_import_v6.py
"""
import py_compile

PATH = "support_bot/kb_import.py"
src = open(PATH, encoding="utf-8").read()

if "JUNK_Q_RE" in src:
    print("guard: already present (skip)")
else:
    anchor = '''SKIP = {"00-index.md", "KB_SCREENSHOT_LINKS.md"}'''
    assert src.count(anchor) == 1, "anchor SKIP не найден"
    addition = anchor + '''
import re as _re
JUNK_Q_RE = _re.compile(r"(?i)тестовая|(^|[^а-я])тест([^а-я]|$)|открыть чат и ответить|"
                        r"как написать в макс|max сообщения →|проверка связи с ботом|"
                        r"нашли чат по этой ссылке")'''
    src = src.replace(anchor, addition, 1)
    anchor2 = '''        if ans:
            arts.append((title, keywords, ans, cat, shots, rel))'''
    assert src.count(anchor2) == 1, "anchor parse_file не найден"
    addition2 = '''        if ans and not JUNK_Q_RE.search(title):
            arts.append((title, keywords, ans, cat, shots, rel))'''
    src = src.replace(anchor2, addition2, 1)
    open(PATH, "w", encoding="utf-8", newline="\n").write(src)
    print("guard: inserted")

py_compile.compile(PATH, doraise=True)
print("PATCH_IMPORT_OK=1")