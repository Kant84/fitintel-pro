from pathlib import Path

root = Path(r"C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop")

# 1. Найти ВСЕ settings_tab.py
print("=== ВСЕ settings_tab.py ===")
for p in root.rglob("settings_tab.py"):
    print(f"  {p}")
    # Показать первые 3 строки
    lines = p.read_text(encoding="utf-8").split('\n')[:3]
    for l in lines:
        print(f"    {l.strip()}")

# 2. Найти импорт в main.py
print("\n=== Импорт SettingsTab в main.py ===")
main = root / "main.py"
if main.exists():
    for i, line in enumerate(main.read_text(encoding="utf-8").split('\n'), 1):
        if 'settings_tab' in line.lower() or 'SettingsTab' in line:
            print(f"  строка {i}: {line.strip()}")

# 3. Найти ВСЕ __pycache__
print("\n=== ВСЕ __pycache__ ===")
for p in root.rglob("__pycache__"):
    print(f"  {p}")
    # Найти settings_tab внутри
    for f in p.glob("*settings_tab*"):
        print(f"    → {f.name}")

print("\n=== РЕКОМЕНДАЦИЯ ===")
print("Удалите ВСЕ __pycache__:")
print(f'Remove-Item -Recurse -Force "{root}\\__pycache__"')
for p in root.rglob("__pycache__"):
    print(f'Remove-Item -Recurse -Force "{p}"')