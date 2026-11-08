import py_compile
PATH = "support_bot/kb_import.py"
src = open(PATH, encoding="utf-8").read()
changed = False
JUNK = 'JUNK_TITLES = {"Тестовая отправка (подвкладка «Тест»)", "Открыть чат и ответить клиенту", "Через «Помощь → Чат с клиентами (MAX)»"}'
if "JUNK_TITLES" not in src:
    a = "ART_RE = re.compile"
    assert src.count(a) == 1, "anchor ART_RE"
    src = src.replace(a, JUNK + "\n\n" + a, 1)
    b = "        if ans:"
    assert src.count(b) == 1, "anchor if ans"
    src = src.replace(b, "        if ans and title.strip() not in JUNK_TITLES:", 1)
    changed = True
    print("junk-guard: inserted")
else:
    print("junk-guard: already present")
if "install-01-setup" not in src:
    c = '"rbac-01": "users-01"'
    assert src.count(c) == 1, "anchor rbac"
    add = (",\n    \"install-01-setup\": \"install-03-wizard-address\","
           "\n    \"install-03-setup-server\": \"install-03-wizard-address\","
           "\n    \"install-04-setup-license\": \"install-04-wizard-license\"")
    src = src.replace(c, c + add, 1)
    changed = True
    print("install-aliases: inserted")
else:
    print("install-aliases: already present")
if changed:
    open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("PATCH_OK=1")
