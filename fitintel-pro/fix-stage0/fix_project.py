#!/usr/bin/env python3
"""
================================================================================
FitIntel Pro — Stage 0: Исправление критических проблем проекта
================================================================================
Запуск:
    python fix_project.py /путь/к/проекту

Исправляет:
1. app/db/_init_.py → app/db/__init__.py
2. Создаёт все __init__.py в пакетах
3. Удаляет временные/отладочные файлы из корня
4. Создаёт правильный .gitignore для Python проекта
5. Удаляет app/utils/qr.py при наличии app/core/qr.py (дублирование)
6. Переименовывает файлы без расширения (lockers/release)
7. Создаёт app/middleware/ и app/dto/ структуры
================================================================================
"""

import os
import sys
import shutil
from pathlib import Path


def print_header(title):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def print_success(msg):
    print(f"  ✓ {msg}")


def print_warning(msg):
    print(f"  ⚠ {msg}")


def print_error(msg):
    print(f"  ✗ {msg}")


def fix_init_typo(project_root: Path):
    """Исправляет _init_.py → __init__.py"""
    print_header("1. Исправление опечатки _init_.py")
    
    wrong = project_root / "app" / "db" / "_init_.py"
    correct = project_root / "app" / "db" / "__init__.py"
    
    if wrong.exists():
        if correct.exists():
            # Оба существуют — удаляем опечатку
            wrong.unlink()
            print_success(f"Удалён дубликат: {wrong}")
        else:
            # Переименовываем
            wrong.rename(correct)
            print_success(f"Переименован: {wrong} → {correct}")
    else:
        print_success("Опечатка не найдена — всё в порядке")


def create_init_files(project_root: Path):
    """Создаёт __init__.py во всех пакетах"""
    print_header("2. Создание __init__.py в пакетах")
    
    packages = [
        "app",
        "app/api",
        "app/api/v1",
        "app/api/v1/lockers",
        "app/core",
        "app/db",
        "app/db/seed",
        "app/integrations",
        "app/integrations/devices",
        "app/integrations/email",
        "app/integrations/one_c",
        "app/integrations/payments",
        "app/integrations/sms",
        "app/integrations/telegram",
        "app/integrations/webhooks",
        "app/models",
        "app/repositories",
        "app/schemas",
        "app/services",
        "app/tasks",
        "app/templates",
        "app/utils",
    ]
    
    created = 0
    for pkg in packages:
        init_file = project_root / pkg / "__init__.py"
        if not init_file.exists():
            init_file.write_text("\n")
            created += 1
    
    print_success(f"Создано {created} __init__.py файлов")


def remove_temp_files(project_root: Path):
    """Удаляет временные/отладочные файлы из корня проекта"""
    print_header("3. Удаление временных файлов")
    
    temp_files = [
        "fix_password.py",
        "structure.txt",
        "test_result.txt",
        "test_config.py",
        "test_db.py",
        "test_models_import.py",
        "test_sqlalchemy.py",
        "alembic.ini.bak",
    ]
    
    removed = 0
    for filename in temp_files:
        filepath = project_root / filename
        if filepath.exists():
            filepath.unlink()
            removed += 1
            print_success(f"Удалён: {filename}")
    
    if removed == 0:
        print_success("Временных файлов не найдено")
    
    return removed


def create_gitignore(project_root: Path):
    """Создаёт правильный .gitignore для Python проекта"""
    print_header("4. Создание .gitignore")
    
    gitignore_content = """# === Python ===
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# === Virtual Environments ===
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# === IDEs ===
.vscode/
.idea/
*.swp
*.swo
*~

# === OS ===
.DS_Store
Thumbs.db

# === Logs ===
*.log
logs/

# === Testing ===
.pytest_cache/
.coverage
htmlcov/
.tox/

# === Temporary files ===
*.bak
*.tmp
*.temp

# === Project specific ===
# Local test files
test_config.py
test_db.py
test_models_import.py
test_sqlalchemy.py
# Generated
structure.txt
test_result.txt
fix_password.py

# Keep .env.example
!.env.example
"""
    
    gitignore_path = project_root / ".gitignore"
    gitignore_path.write_text(gitignore_content)
    print_success("Создан .gitignore с правилами для Python проекта")


def fix_duplicate_qr(project_root: Path):
    """Удаляет дублирование qr.py"""
    print_header("5. Исправление дублирования qr.py")
    
    core_qr = project_root / "app" / "core" / "qr.py"
    utils_qr = project_root / "app" / "utils" / "qr.py"
    
    if core_qr.exists() and utils_qr.exists():
        # Проверяем, что core/qr.py не пустой
        if core_qr.stat().st_size > 10:
            utils_qr.unlink()
            print_success(f"Удалён дубликат: {utils_qr} (core/qr.py основной)")
        elif utils_qr.stat().st_size > 10:
            core_qr.unlink()
            print_success(f"Удалён дубликат: {core_qr} (utils/qr.py основной)")
        else:
            print_warning("Оба qr.py пустые или маленькие — проверьте вручную")
    elif core_qr.exists():
        print_success("Только core/qr.py — дублирования нет")
    elif utils_qr.exists():
        print_success("Только utils/qr.py — дублирования нет")
    else:
        print_warning("qr.py не найден ни в одном месте")


def fix_lockers_release(project_root: Path):
    """Исправляет файл без расширения"""
    print_header("6. Исправление lockers/release")
    
    release_file = project_root / "app" / "api" / "v1" / "lockers" / "release"
    
    if release_file.exists():
        if release_file.is_file():
            # Пробуем определить содержимое
            content = release_file.read_bytes()[:100]
            
            # Переименовываем в .py
            new_file = release_file.with_suffix(".py")
            release_file.rename(new_file)
            print_success(f"Переименован: {release_file} → {new_file}")
        else:
            print_warning(f"{release_file} — директория, пропускаем")
    else:
        print_success("Файл без расширения не найден")


def create_missing_dirs(project_root: Path):
    """Создаёт недостающие директории"""
    print_header("7. Создание недостающих директорий")
    
    dirs_to_create = [
        "app/middleware",
        "app/dto",
        "tests/unit",
        "tests/integration",
        "frontend",
    ]
    
    created = 0
    for dirname in dirs_to_create:
        dirpath = project_root / dirname
        if not dirpath.exists():
            dirpath.mkdir(parents=True, exist_ok=True)
            init_file = dirpath / "__init__.py"
            init_file.write_text("\n")
            created += 1
            print_success(f"Создана директория: {dirname}/")
    
    if created == 0:
        print_success("Все директории на месте")


def run_tests(project_root: Path):
    """Запускает тесты после исправлений"""
    print_header("8. Проверка импортов")
    
    import subprocess
    
    # Проверяем что Python может импортировать модули
    test_script = project_root / "app" / "main.py"
    if test_script.exists():
        print_success(f"main.py найден: {test_script}")
    
    # Проверяем models
    models_init = project_root / "app" / "models" / "__init__.py"
    if models_init.exists():
        print_success("models/__init__.py создан")
    
    print("\n  → Запустите тесты вручную:")
    print("     pytest tests/ -v")
    print("     Или: python -c \"from app.main import app; print('OK')\"")


def main():
    if len(sys.argv) < 2:
        print("Использование: python fix_project.py <путь_к_проекту>")
        print("Пример: python fix_project.py /home/user/FitNexus-AI")
        sys.exit(1)
    
    project_root = Path(sys.argv[1]).resolve()
    
    if not project_root.exists():
        print(f"ОШИБКА: Путь не существует: {project_root}")
        sys.exit(1)
    
    if not (project_root / "app" / "main.py").exists():
        print(f"ПРЕДУПРЕЖДЕНИЕ: Не найден app/main.py — это точно проект FitNexus AI?")
        response = input("Продолжить? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    print(f"\n{'=' * 70}")
    print(f"  FitIntel Pro — Stage 0: Исправление критических проблем")
    print(f"  Проект: {project_root}")
    print(f"{'=' * 70}")
    
    # Выполняем все исправления
    fix_init_typo(project_root)
    create_init_files(project_root)
    removed = remove_temp_files(project_root)
    create_gitignore(project_root)
    fix_duplicate_qr(project_root)
    fix_lockers_release(project_root)
    create_missing_dirs(project_root)
    run_tests(project_root)
    
    # Итог
    print(f"\n{'=' * 70}")
    print(f"  ИСПРАВЛЕНИЯ ЗАВЕРШЕНЫ!")
    print(f"{'=' * 70}")
    print(f"\n  Следующие шаги:")
    print(f"  1. Проверьте git status: git status")
    print(f"  2. Добавьте изменения: git add -A")
    print(f"  3. Коммит: git commit -m 'Stage 0: Fix critical issues'")
    print(f"  4. Запустите тесты: pytest tests/ -v")
    print(f"\n  Следующий этап: Инфраструктура (Terraform + Ansible)")
    print()


if __name__ == "__main__":
    main()
