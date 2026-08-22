import io
import re
import glob

TABLE_RE = re.compile(
    r'\.setStyleSheet\("""\s*\n\s*QTableWidget \{ background: #ffffff;.*?"""\)', re.S)
CARD_RE = re.compile(
    r'\.setStyleSheet\("background: #ffffff; border: 1px solid #e2e8f0;[^"]*"\)')

for p in glob.glob("windows/*_tab.py"):
    src = io.open(p, encoding="utf-8").read()
    orig = src
    if "from windows import theme" not in src:
        src = src.replace("from api import ApiClient",
                          "from api import ApiClient\nfrom windows import theme", 1)
    # карточки: цвета текста в f-string HTML
    src = src.replace("color:#0f172a;", "color:{theme.fg()};")
    src = src.replace("color:#64748b;", "color:{theme.sub()};")
    # карточки: фон
    src = CARD_RE.sub(".setStyleSheet(theme.card_style())", src)
    # таблицы
    src = TABLE_RE.sub(".setStyleSheet(theme.table_style())", src)
    # жёлтый баннер сегментов в dashboard
    src = src.replace(
        '.setStyleSheet("background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px; font-size: 13px;")',
        ".setStyleSheet(theme.banner_style())")
    if src != orig:
        io.open(p, "w", encoding="utf-8").write(src)
        print("PATCHED", p)
    else:
        print("skip", p)
