# -*- coding: utf-8 -*-
"""apply_icons.py — встраивает иконки FitIntel Pro в десктоп (1.6.1).
Идемпотентен: повторный запуск безопасен. Вывод отчёта — что сделано, что не найдено."""
from pathlib import Path
import shutil, re, py_compile

ROOT = Path(__file__).resolve().parent
DESK = ROOT / "fitintel-desktop"
ASSETS = DESK / "assets"
ICONS_SRC = Path(r"E:\FitNexus AI\Иконки")

MARK_WIN = "# ICONS-APPLY: window icon"
MARK_LOGO = "# ICONS-APPLY: login logo"

report = []

# ── 1. Копируем иконки в assets ──────────────────────────────
ASSETS.mkdir(exist_ok=True)
copies = [
    ("fitintel.ico",         "FitIntel_icon.ico"),
    ("fitintel_icon_512.png",  "app_icon_512.png"),
    ("fitintel_icon_1024.png", "app_icon_1024.png"),
    ("fitintel_wave.png",      "logo_wave.png"),
]
for src_name, dst_name in copies:
    src, dst = ICONS_SRC / src_name, ASSETS / dst_name
    if not src.exists():
        report.append(f"!! НЕТ ИСТОЧНИКА: {src}")
        continue
    shutil.copy2(src, dst)
    report.append(f"OK иконка: {dst_name} ({dst.stat().st_size} байт)")

# ── 2. Иконка окна во всех окнах + Alt+Tab (main.py) ─────────
main_py = DESK / "main.py"
if main_py.exists():
    src = main_py.read_text(encoding="utf-8")
    if MARK_WIN in src:
        report.append("-- main.py: иконка уже встроена")
    else:
        m = re.search(r'^([ \t]*\w+[ \t]*=[ \t]*QApplication\([^)]*\)[ \t]*)$', src, re.M)
        if m:
            block = (
                f"\n{MARK_WIN}\n"
                "try:\n"
                "    from PyQt6.QtGui import QIcon as _AppIcon\n"
                "    from pathlib import Path as _P\n"
                "    _ic = _P(__file__).parent / 'assets' / 'app_icon_512.png'\n"
                "    if _ic.exists():\n"
                "        app.setWindowIcon(_AppIcon(str(_ic)))\n"
                "except Exception:\n"
                "    pass\n"
            )
            src = src.replace(m.group(1), m.group(1) + block, 1)
            main_py.write_text(src, encoding="utf-8")
            report.append("OK main.py: иконка окна встроена")
        else:
            report.append("!! main.py: строка 'QApplication(' не найдена — впишите вручную")
    try:
        py_compile.compile(str(main_py), doraise=True)
        report.append("OK main.py: синтаксис")
    except Exception as e:
        report.append(f"!! main.py: ОШИБКА СИНТАКСИСА {e}")
else:
    report.append("!! main.py не найден")

# ── 3. Логотип на окне входа (login_window.py) ───────────────
login_py = DESK / "windows" / "login_window.py"
if login_py.exists():
    src = login_py.read_text(encoding="utf-8")
    if MARK_LOGO in src:
        report.append("-- login_window.py: логотип уже встроен")
    else:
        m = re.search(r'^(?P<ind>[ \t]*)def _build_ui\(self\):\n(?P<body>(?:[ \t]+.*\n){0,40}?)'
                      r'(?P<lind>[ \t]*)(\w+)[ \t]*=[ \t]*QVBoxLayout\(', src)
        if m:
            ind = m.group("lind") or "        "
            var = m.group(5)
            block = (
                f"{ind}{MARK_LOGO}\n"
                f"{ind}try:\n"
                f"{ind}    from PyQt6.QtGui import QPixmap as _PM\n"
                f"{ind}    from PyQt6.QtWidgets import QLabel as _Lbl\n"
                f"{ind}    from pathlib import Path as _P2\n"
                f"{ind}    _lg = _P2(__file__).resolve().parents[1] / 'assets' / 'logo_wave.png'\n"
                f"{ind}    if _lg.exists():\n"
                f"{ind}        _l = _Lbl()\n"
                f"{ind}        _l.setPixmap(_PM(str(_lg)).scaledToWidth(220))\n"
                f"{ind}        _l.setAlignment(Qt.AlignmentFlag.AlignCenter)\n"
                f"{ind}        {var}.addWidget(_l)\n"
                f"{ind}except Exception:\n"
                f"{ind}    pass\n"
            )
            src = src[:m.end()] + "\n" + block + src[m.end():]
            login_py.write_text(src, encoding="utf-8")
            report.append(f"OK login_window.py: логотип встроен (layout: {var})")
        else:
            report.append("!! login_window.py: не нашёл '_build_ui' + 'QVBoxLayout' — покажите файл")
    try:
        py_compile.compile(str(login_py), doraise=True)
        report.append("OK login_window.py: синтаксис")
    except Exception as e:
        report.append(f"!! login_window.py: ОШИБКА СИНТАКСИСА {e}")
else:
    report.append("!! login_window.py не найден")

# ── 4. Проверяем/добавляем assets в spec ─────────────────────
spec = DESK / "FitIntelDesktop.spec"
if spec.exists():
    s = spec.read_text(encoding="utf-8")
    if re.search(r"['\"]assets['\"]", s):
        report.append("OK spec: assets уже в datas")
    else:
        m = re.search(r'datas[ \t]*=[ \t]*\[\s*', s)
        if m:
            s = s[:m.end()] + "\n        ('assets', 'assets')," + s[m.end():]
            spec.write_text(s, encoding="utf-8")
            report.append("OK spec: ('assets','assets') добавлено в datas")
        else:
            report.append("!! spec: список datas не найден — пришлите FitIntelDesktop.spec")
else:
    report.append("!! FitIntelDesktop.spec не найден")

print("\n".join(report))
print("\nГотово. Дальше: python main.py (проверка) → pyinstaller → Inno Setup (F9)")