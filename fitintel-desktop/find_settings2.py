from pathlib import Path

root = Path(r"C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop")

print("=== ГДЕ ИМПОРТИРУЕТСЯ SettingsTab ===")
for py_file in root.rglob("*.py"):
    try:
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.split('\n'), 1):
            if 'SettingsTab' in line or 'settings_tab' in line.lower():
                print(f"  {py_file.relative_to(root)}:{i} → {line.strip()}")
    except Exception:
        pass