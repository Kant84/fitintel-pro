# -*- coding: utf-8 -*-
"""Автопатч desktop: кнопка «Поддержка разработчика → Открыть MAX» открывает чат
с автопривязкой клуба (deeplink ?start=<префикс ключа лицензии>).

Запуск из корня репозитория:  python patch_desktop_support.py
Идемпотентен (повторный запуск ничего не меняет). Каждый файл проверяется
компиляцией. Стопорится с ясным сообщением, если якорь не найден.
"""
import os, re, sys, tempfile, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.join(ROOT, "fitintel-desktop", "windows")
results = []

FUNC = (
    "\n\n"
    "def _support_url() -> str:\n"
    "    \"\"\"Чат поддержки; с сохранённым ключом — автопривязка клуба (?start=префикс ключа).\"\"\"\n"
    "    base = MAX_SUPPORT_URL\n"
    "    try:\n"
    "        import json as _cj, os as _os\n"
    "        try:\n"
    "            from paths import APP_DIR\n"
    "            cfgp = str(APP_DIR / \"client_settings.json\")\n"
    "        except Exception:\n"
    "            cfgp = \"client_settings.json\"\n"
    "        if _os.path.exists(cfgp):\n"
    "            key = (_cj.load(open(cfgp, encoding=\"utf-8\")).get(\"license_key\") or \"\")\n"
    "            if key.startswith(\"FIPRO-\") and len(key) >= 24:\n"
    "                return base + \"?start=\" + key[:24]\n"
    "    except Exception:\n"
    "        pass\n"
    "    return base"
)

SAVE_KEY_BLOCK_ACT = (
    "\n\n"
    "        try:\n"
    "            from paths import APP_DIR\n"
    "            import os as _os, json as _json\n"
    "            cfgp = str(APP_DIR / \"client_settings.json\")\n"
    "            cfg = _json.load(open(cfgp, encoding=\"utf-8\")) if _os.path.exists(cfgp) else {}\n"
    "            cfg[\"license_key\"] = key\n"
    "            _json.dump(cfg, open(cfgp, \"w\", encoding=\"utf-8\"), ensure_ascii=False, indent=2)\n"
    "        except Exception:\n"
    "            pass"
)

def read(p):
    return open(p, encoding="utf-8").read()

def write(p, s):
    open(p, "w", encoding="utf-8", newline="\n").write(s)

def compile_check(p):
    py_compile.compile(p, cfile=os.path.join(tempfile.gettempdir(), "chk_%d.pyc" % os.getpid()), doraise=True)

# ── 1) help_dialog.py ────────────────────────────────────────────────────────
p = os.path.join(DESK, "help_dialog.py")
s = read(p)
if "def _support_url" not in s:
    anchor = 'MAX_SUPPORT_URL = "https://max.ru/fitintel_support"  # TODO: заменить на реальный чат разработчика'
    assert anchor in s, "help_dialog: якорь MAX_SUPPORT_URL не найден — файл менялся вручную?"
    s = s.replace(anchor, anchor + FUNC, 1)
    results.append("help_dialog: + _support_url()")
else:
    results.append("help_dialog: уже (функция есть)")
t_disp = '"• MAX: " + MAX_SUPPORT_URL + "\\n\\n"'
if t_disp in s:
    s = s.replace(t_disp, '"• MAX: " + _support_url() + "\\n\\n"')
    results.append("help_dialog: строка показа -> _support_url()")
t_open = "os.startfile(MAX_SUPPORT_URL)"
if t_open in s:
    s = s.replace(t_open, "os.startfile(_support_url())")
    results.append("help_dialog: открытие -> _support_url()")
write(p, s); compile_check(p)

# ── 2) activation_dialog.py (первый запуск) ──────────────────────────────────
p = os.path.join(DESK, "activation_dialog.py")
s = read(p)
if 'cfg["license_key"] = key' in s:
    results.append("activation_dialog: уже (сохранение есть)")
else:
    anchor = ('        if not r.get("activated"):\n'
              '            self.lbl.setText("Ключ не принят: " + str(r.get("reason", r))[:180])\n'
              '            return')
    assert anchor in s, "activation_dialog: якорь activated-блока не найден"
    s = s.replace(anchor, anchor + SAVE_KEY_BLOCK_ACT, 1)
    results.append("activation_dialog: + сохранение ключа")
write(p, s); compile_check(p)

# ── 3) license_tab.py (E68: панель «Проверить и активировать») ───────────────
p = os.path.join(DESK, "license_tab.py")
s = read(p)
if "[E68] save license_key" in s:
    results.append("license_tab: уже (сохранение есть)")
else:
    m = re.search(r'(?m)^(\s*)res\.setText\(f"\s*Лицензия активирована.*$', s)
    assert m, "license_tab: строка res.setText(...Лицензия активирована...) не найдена"
    ind = m.group(1)
    block = (
        ind + "try:\n"
        + ind + "    import json as _cj, os as _os\n"
        + ind + "    cfgp = str(_e68_settings_path())\n"
        + ind + '    cfg = _cj.load(open(cfgp, encoding="utf-8")) if _os.path.exists(cfgp) else {}\n'
        + ind + '    cfg["license_key"] = key\n'
        + ind + '    _cj.dump(cfg, open(cfgp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)\n'
        + ind + "except Exception as _e:\n"
        + ind + '    print("[E68] save license_key:", _e)\n'
    )
    s = s[:m.end()] + "\n" + block + s[m.end():]
    results.append("license_tab: + сохранение ключа")
write(p, s); compile_check(p)

for r in results:
    print(r)
print("DESKTOP_PATCH_OK=1")
