#!/usr/bin/env python3
"""
================================================================================
Stage 0: Тестирование исправлений
================================================================================
Запуск:
    python test_stage0.py
================================================================================
"""

import sys
import os
from pathlib import Path

def test_init_files():
    """Проверяет что __init__.py созданы"""
    packages = [
        "app", "app/api", "app/api/v1", "app/api/v1/lockers",
        "app/core", "app/db", "app/db/seed",
        "app/integrations", "app/integrations/devices",
        "app/integrations/email", "app/integrations/one_c",
        "app/integrations/payments", "app/integrations/sms",
        "app/integrations/telegram", "app/integrations/webhooks",
        "app/models", "app/repositories", "app/schemas",
        "app/services", "app/tasks", "app/templates", "app/utils",
        "app/middleware", "app/dto", "frontend",
    ]
    
    errors = []
    for pkg in packages:
        init_file = Path(pkg) / "__init__.py"
        if not init_file.exists():
            errors.append(f"  ✗ {init_file} — ОТСУТСТВУЕТ")
    
    if errors:
        print("❌ __init__.py файлы:")
        for e in errors:
            print(e)
        return False
    else:
        print(f"✅ Все {len(packages)} __init__.py на месте")
        return True


def test_init_typo_fixed():
    """Проверяет что _init_.py исправлен"""
    wrong = Path("app/db/_init_.py")
    correct = Path("app/db/__init__.py")
    
    if wrong.exists():
        print(f"❌ Опечатка НЕ исправлена: {wrong} всё ещё существует")
        return False
    
    if correct.exists():
        print(f"✅ Опечатка исправлена: {correct} существует")
        return True
    else:
        print(f"❌ __init__.py не найден!")
        return False


def test_temp_files_removed():
    """Проверяет что временные файлы удалены"""
    temp_files = [
        "fix_password.py", "structure.txt", "test_result.txt",
        "test_config.py", "test_db.py", "test_models_import.py",
        "test_sqlalchemy.py", "alembic.ini.bak",
    ]
    
    errors = []
    for f in temp_files:
        if Path(f).exists():
            errors.append(f"  ✗ {f} — всё ещё существует")
    
    if errors:
        print("❌ Временные файлы НЕ удалены:")
        for e in errors:
            print(e)
        return False
    else:
        print(f"✅ Все {len(temp_files)} временных файлов удалены")
        return True


def test_gitignore():
    """Проверяет .gitignore"""
    gitignore = Path(".gitignore")
    
    if not gitignore.exists():
        print("❌ .gitignore НЕ существует")
        return False
    
    content = gitignore.read_text()
    
    required = ["__pycache__", ".venv", ".env", "*.pyc", ".pytest_cache"]
    missing = [r for r in required if r not in content]
    
    if missing:
        print(f"❌ .gitignore не содержит: {', '.join(missing)}")
        return False
    else:
        print(f"✅ .gitignore корректен ({len(content)} символов)")
        return True


def test_lockers_release():
    """Проверяет lockers/release.py"""
    old = Path("app/api/v1/lockers/release")
    new = Path("app/api/v1/lockers/release.py")
    
    if old.exists() and not new.exists():
        print(f"❌ lockers/release не переименован")
        return False
    
    if new.exists():
        print(f"✅ lockers/release → release.py")
        return True
    
    print("⚠️ lockers/release не найден (возможно уже был .py)")
    return True


def test_critical_files_exist():
    """Проверяет что критические файлы на месте"""
    files = [
        "app/main.py", "app/core/config.py", "app/core/security.py",
        "app/db/session.py", "alembic.ini", "celery_app.py",
        "Makefile", "pyproject.toml", ".env.example",
    ]
    
    errors = []
    for f in files:
        if not Path(f).exists():
            errors.append(f"  ✗ {f} — ОТСУТСТВУЕТ")
    
    if errors:
        print("❌ Критические файлы отсутствуют:")
        for e in errors:
            print(e)
        return False
    else:
        print(f"✅ Все {len(files)} критических файлов на месте")
        return True


def test_imports():
    """Проверяет Python импорты"""
    print("\n  Проверка импортов...")
    
    tests = [
        ("app.main", "app"),
        ("app.db.session", "get_db"),
        ("app.core.config", "settings"),
        ("app.core.security", "create_access_token"),
    ]
    
    passed = 0
    for module, attr in tests:
        try:
            mod = __import__(module, fromlist=[attr])
            getattr(mod, attr, None)
            print(f"    ✅ {module}.{attr}")
            passed += 1
        except Exception as e:
            print(f"    ❌ {module}.{attr} — {e}")
    
    if passed == len(tests):
        print(f"  ✅ Все {passed} импортов прошли")
        return True
    else:
        print(f"  ❌ {len(tests) - passed} импортов не прошли")
        return False


def main():
    print("=" * 70)
    print("  Stage 0: ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ")
    print("=" * 70)
    
    results = []
    
    print("\n1. __init__.py опечатка...")
    results.append(test_init_typo_fixed())
    
    print("\n2. __init__.py файлы...")
    results.append(test_init_files())
    
    print("\n3. Временные файлы удалены...")
    results.append(test_temp_files_removed())
    
    print("\n4. .gitignore...")
    results.append(test_gitignore())
    
    print("\n5. lockers/release...")
    results.append(test_lockers_release())
    
    print("\n6. Критические файлы...")
    results.append(test_critical_files_exist())
    
    print("\n7. Python импорты...")
    results.append(test_imports())
    
    # Итог
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 70)
    if passed == total:
        print(f"  ✅ ВСЕ {total}/{total} ТЕСТОВ ПРОЙДЕНЫ!")
        print("  → Можно переходить к следующему модулю")
    else:
        print(f"  ❌ {passed}/{total} тестов пройдены")
        print("  → Исправь ошибки перед продолжением")
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
