"""
test_main.py — pytest-совместимый тест для проверки app/main.py
Запуск из корня проекта:  python test_main.py
"""
import re
import sys
from collections import Counter
from pathlib import Path


def test_main_routers():
    main_path = Path("app/main.py")
    assert main_path.exists(), "app/main.py не найден! Запустите из корня проекта."

    content = main_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    errors = []

    # 1. Дубли include_router
    includes = re.findall(r'app\.include_router\((\w+)', content)
    dup_includes = {k: v for k, v in Counter(includes).items() if v > 1}
    if dup_includes:
        errors.append(f"❌ Дубли include_router: {dup_includes}")

    # 2. Дубли импортов router as
    imports = re.findall(r'from\s+([\w.]+)\s+import\s+router\s+as\s+(\w+)', content)
    import_names = [name for _, name in imports]
    dup_imports = {k: v for k, v in Counter(import_names).items() if v > 1}
    if dup_imports:
        errors.append(f"❌ Дубли импортов: {dup_imports}")

    # 3. Хардкод /api/v1 (кроме спец. случаев)
    hardcoded = []
    for i, line in enumerate(lines, 1):
        if 'prefix="/api/v1"' in line:
            if 'document-templates' in line or '_la.router' in line or 'E66' in line:
                continue
            hardcoded.append(f"  строка {i}: {line.strip()[:70]}")
    if hardcoded:
        errors.append(f"❌ Хардкод prefix=\"/api/v1\" ({len(hardcoded)} шт.):")
        errors.extend(hardcoded)

    # 4. license_router — конфликт имён
    license_imports = [name for mod, name in imports if 'license' in mod or 'license' in name]
    if len(license_imports) > 1 and len(set(license_imports)) < len(license_imports):
        errors.append(f"❌ Конфликт имён license-роутеров: {license_imports}")

    # 5. dynamic_qr_router — только 1
    if includes.count("dynamic_qr_router") != 1:
        errors.append(f"❌ dynamic_qr_router: {includes.count('dynamic_qr_router')} раз(а)")

    # 6. notifications_router — только 1
    if includes.count("notifications_router") != 1:
        errors.append(f"❌ notifications_router: {includes.count('notifications_router')} раз(а)")

    # 7. Нестандартные префиксы
    bad_prefix = []
    for i, line in enumerate(lines, 1):
        m = re.search(r'app\.include_router\((\w+),\s*prefix=(.+?)\)', line)
        if m:
            router_name, prefix = m.groups()
            prefix = prefix.strip()
            if prefix == '"/api/v1"' and router_name not in ('_la',):
                bad_prefix.append(f"  строка {i}: {router_name} → {prefix}")
    if bad_prefix:
        errors.append(f"❌ Нестандартные префиксы ({len(bad_prefix)} шт.):")
        errors.extend(bad_prefix)

    if errors:
        print("\n".join(errors))
        print(f"\n❌ Тест НЕ ПРОЙДЕН. Найдено проблем: {len([e for e in errors if e.startswith('❌')])}")
        sys.exit(1)
    else:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ:")
        print(f"   • Уникальных роутеров: {len(set(includes))}")
        print(f"   • Всего include_router: {len(includes)}")
        print(f"   • Дублей: 0 | Хардкода: 0 | Конфликтов: 0")
        sys.exit(0)


if __name__ == "__main__":
    test_main_routers()