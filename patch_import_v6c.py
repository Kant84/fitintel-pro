# -*- coding: utf-8 -*-
'''Патч support_bot/kb_import.py (v3.1): мусор-фильтр на импорте + алиасы install-скринов.
Запуск: python patch_import_v6c.py'''
import py_compile, re as _re
NL = chr(10)
PATH = "support_bot/kb_import.py"
src = open(PATH, encoding="utf-8").read()
changed = False
if "JUNK_Q_RE" not in src:
    ins = "JUNK_Q_RE = _re.compile(r'(?i)тестовая|(^|[^а-я])тест([^а-я]|$)|открыть чат и ответить|как написать в макс|проверка связи с ботом|нашли чат по этой ссылке|запустить бота|скачать приложение')" + NL + NL
    anchor = "ART_RE = re.compile"
    assert src.count(anchor) == 1, "anchor ART_RE не найден"
    src = src.replace(anchor, ins + anchor, 1)
    anchor2 = "        if ans:"
    assert src.count(anchor2) == 1, "anchor parse-loop не найден"
    src = src.replace(anchor2, "        if ans and not JUNK_Q_RE.search(title):", 1)
    changed = True
    print("junk-guard: inserted")
else:
    print("junk-guard: already present (skip)")
if "install-01-setup" not in src:
    anchor3 = "    ""rbac-01"": ""users-01"","
    assert src.count(anchor3) == 1, "anchor ALIAS-rbac не найден"
    add = (NL + "    ""install-01-setup"": ""install-03-wizard-address"","
           "    ""install-03-setup-server"": ""install-03-wizard-address"","
           "    ""install-04-setup-license"": ""install-04-wizard-license"",")
    src = src.replace(anchor3, anchor3 + add, 1)
    changed = True
    print("install-aliases: inserted")
else:
    print("install-aliases: already present (skip)")
if changed:
    open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("PATCH_IMPORT_OK=1")