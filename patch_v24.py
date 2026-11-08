# -*- coding: utf-8 -*-
# Патч support_bot/app.py -> v24:
# 1) словарь опечаток в normalize (турнет->турникет, абонемант->абонемент, сдлать->сделать, неработает->не работает)
# 2) word_similarity порог 0.55 -> 0.4 (общая страховка опечаток)
# 3) FTS rank floor 0.01 -> 0.005 (excel-выгрузка)
# 4) offtopic_hit не отсекает грубые обращения (FRUSTRATED идут в деэскалацию, а не в отказ)
import re, py_compile
PATH = "support_bot/app.py"
src = open(PATH, encoding="utf-8").read()

# 1) опечатки в normalize
anchor = "    return \" \".join(q.split())"
assert src.count(anchor) >= 1, "normalize tail"
typo_block = ("    for _b, _g in {\"турнет\": \"турникет\", \"абонемант\": \"абонемент\", \"сдлать\": \"сделать\", "
              "\"неработает\": \"не работает\", \"абонемен\": \"абонемент\", \"вернуть\": \"возврат\"}.items():\n"
              "        q = re.sub(r\"\\b\" + _b + r\"\\b\", _g, q)\n")
if "турнет" not in src:
    src = src.replace(anchor, typo_block + anchor, 1)
    print("typo-dict: inserted")
else:
    print("typo-dict: already present")

# 2) порог word_similarity
c = src.count(">= 0.55")
if c:
    src = src.replace(">= 0.55", ">= 0.4")
    print(f"word-sim threshold: {c} replaced")
else:
    print("word-sim threshold: already 0.4 or not found")

# 3) rank floor
if ">= 0.01" in src:
    src = src.replace("if row and float(row[3]) >= 0.01:", "if row and float(row[3]) >= 0.005:")
    print("fts floor: 0.01 -> 0.005")
else:
    print("fts floor: already changed")

# 4) offtopic не отсекает FRUSTRATED
anchor2 = "    return singles >= 2"
if anchor2 in src and "not any(f in t for f in FRUSTRATED)" not in src:
    assert src.count(anchor2) == 1, "offtopic tail"
    src = src.replace(anchor2, "    return singles >= 2 and not any(f in t for f in FRUSTRATED)", 1)
    print("offtopic-vs-frustrated: fixed")
else:
    print("offtopic-vs-frustrated: already ok or anchor missing")

open(PATH, "w", encoding="utf-8", newline="\n").write(src)
py_compile.compile(PATH, doraise=True)
print("V24_PATCH_OK=1")
