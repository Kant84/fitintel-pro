#!/usr/bin/env python3
"""
Скрипт аудита проекта FitNexus AI
Запуск: python audit_project.py <путь_к_проекту>
"""

import os
import sys
from pathlib import Path


def check_file_exists(path: Path, description: str) -> tuple:
    """Проверяет существование файла"""
    exists = path.exists()
    status = "OK" if exists else "ERROR"
    return (status, description, str(path), "Существует" if exists else "ОТСУТСТВУЕТ")


def check_init_files(project_root: Path) -> list:
    """Проверяет наличие __init__.py во всех пакетах"""
    issues = []
    packages = [
        "app",
        "app/api",
        "app/api/v1",
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
    
    for pkg in packages:
        init_file = project_root / pkg / "__init__.py"
        if not init_file.exists():
            issues.append(("ERROR", f"Отсутствует __init__.py", str(init_file), "Создать пустой файл"))
    
    # Проверка на опечатку
    typo_file = project_root / "app/db/_init_.py"
    if typo_file.exists():
        issues.append(("ERROR", "Опечатка в имени файла", str(typo_file), "Переименовать в __init__.py"))
    
    return issues


def check_temp_files(project_root: Path) -> list:
    """Проверяет наличие временных/отладочных файлов"""
    issues = []
    temp_patterns = [
        "fix_password.py",
        "structure.txt", 
        "test_result.txt",
        "test_config.py",
        "test_db.py",
        "test_models_import.py",
        "test_sqlalchemy.py",
        "alembic.ini.bak",
    ]
    
    for pattern in temp_patterns:
        filepath = project_root / pattern
        if filepath.exists():
            issues.append(("WARNING", "Временный/отладочный файл", str(filepath), "Удалить или добавить в .gitignore"))
    
    return issues


def check_structure(project_root: Path) -> list:
    """Проверяет структуру проекта"""
    issues = []
    
    # Проверка файла без расширения
    lockers_release = project_root / "app/api/v1/lockers/release"
    if lockers_release.exists():
        issues.append(("WARNING", "Файл без расширения", str(lockers_release), "Добавить .py или удалить"))
    
    # Проверка дублирования qr.py
    core_qr = project_root / "app/core/qr.py"
    utils_qr = project_root / "app/utils/qr.py"
    if core_qr.exists() and utils_qr.exists():
        issues.append(("WARNING", "Дублирование кода QR", f"{core_qr} + {utils_qr}", "Объединить в один модуль"))
    
    # Проверка .gitignore
    gitignore = project_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if len(content.strip()) < 10:
            issues.append(("WARNING", ".gitignore почти пустой", str(gitignore), "Добавить правила для Python проекта"))
    
    # Проверка наличия middleware
    middleware_dir = project_root / "app/middleware"
    if not middleware_dir.exists():
        issues.append(("WARNING", "Отсутствует middleware", str(middleware_dir), "Создать для CORS, logging, error handling"))
    
    # Проверка наличия dto
    dto_dir = project_root / "app/dto"
    if not dto_dir.exists():
        issues.append(("WARNING", "Отсутствует DTO слой", str(dto_dir), "Создать для чёткого разделения данных"))
    
    return issues


def check_critical_files(project_root: Path) -> list:
    """Проверяет критические файлы"""
    checks = []
    
    critical_files = [
        ("app/main.py", "Главный файл приложения"),
        ("app/core/config.py", "Конфигурация"),
        ("app/core/security.py", "Безопасность"),
        ("app/db/session.py", "Сессии БД"),
        ("app/db/base.py", "Базовые модели"),
        ("alembic.ini", "Alembic конфигурация"),
        ("celery_app.py", "Celery приложение"),
        ("docker-compose.dev.yml", "Docker Compose dev"),
        ("docker-compose.prod.yml", "Docker Compose prod"),
        ("Makefile", "Автоматизация"),
        ("pyproject.toml", "Зависимости"),
        (".env.example", "Пример окружения"),
    ]
    
    for filepath, desc in critical_files:
        full_path = project_root / filepath
        exists = full_path.exists()
        status = "OK" if exists else "ERROR"
        checks.append((status, desc, filepath, "Существует" if exists else "ОТСУТСТВУЕТ"))
    
    return checks


def check_modules(project_root: Path) -> list:
    """Проверяет наличие реализованных модулей"""
    modules = []
    
    module_checks = [
        ("app/api/v1/auth.py", "Auth API"),
        ("app/api/v1/clients.py", "CRM API"),
        ("app/api/v1/tariffs.py", "Tariffs API"),
        ("app/api/v1/subscriptions.py", "Subscriptions API"),
        ("app/api/v1/payments.py", "Payments API"),
        ("app/api/v1/visits.py", "Visits API"),
        ("app/api/v1/access.py", "Access Control API"),
        ("app/models/client.py", "Client Model"),
        ("app/models/subscription.py", "Subscription Model"),
        ("app/models/payment.py", "Payment Model"),
        ("app/models/visit.py", "Visit Model"),
        ("app/models/access.py", "Access Model"),
        ("app/services/auth_service.py", "Auth Service"),
        ("app/services/client_service.py", "Client Service"),
        ("app/services/payment_service.py", "Payment Service"),
        ("app/services/visit_service.py", "Visit Service"),
    ]
    
    for filepath, desc in module_checks:
        full_path = project_root / filepath
        exists = full_path.exists()
        status = "OK" if exists else "ERROR"
        modules.append((status, desc, filepath, "Существует" if exists else "ОТСУТСТВУЕТ"))
    
    return modules


def print_report(title: str, items: list):
    """Печатает секцию отчёта"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    
    if not items:
        print("  Всё в порядке!")
        return
    
    for status, desc, path, recommendation in items:
        icon = "✓" if status == "OK" else "✗" if status == "ERROR" else "⚠"
        color = "\033[92m" if status == "OK" else "\033[91m" if status == "ERROR" else "\033[93m"
        reset = "\033[0m"
        print(f"\n  {color}{icon}{reset} {desc}")
        print(f"    Путь: {path}")
        if recommendation:
            print(f"    Действие: {recommendation}")


def main():
    if len(sys.argv) < 2:
        project_root = Path(".")
    else:
        project_root = Path(sys.argv[1])
    
    if not project_root.exists():
        print(f"ОШИБКА: Путь {project_root} не существует")
        sys.exit(1)
    
    print(f"\n{'#'*80}")
    print(f"#{'':^78}#")
    print(f"#{'FitNexus AI — Аудит проекта':^78}#")
    print(f"#{'':^78}#")
    print(f"{'#'*80}")
    print(f"\n  Проект: {project_root.absolute()}")
    print(f"  Дата: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Собираем все проверки
    all_issues = []
    
    critical = check_critical_files(project_root)
    all_issues.extend(critical)
    
    modules = check_modules(project_root)
    all_issues.extend(modules)
    
    init_issues = check_init_files(project_root)
    all_issues.extend(init_issues)
    
    temp_issues = check_temp_files(project_root)
    all_issues.extend(temp_issues)
    
    structure_issues = check_structure(project_root)
    all_issues.extend(structure_issues)
    
    # Печатаем отчёт
    print_report("КРИТИЧЕСКИЕ ФАЙЛЫ", [i for i in critical if i[0] != "OK"])
    print_report("МОДУЛИ", [i for i in modules if i[0] != "OK"])
    print_report("__init__.py ПАКЕТЫ", init_issues)
    print_report("ВРЕМЕННЫЕ ФАЙЛЫ", temp_issues)
    print_report("СТРУКТУРА", structure_issues)
    
    # Итог
    errors = sum(1 for i in all_issues if i[0] == "ERROR")
    warnings = sum(1 for i in all_issues if i[0] == "WARNING")
    ok = sum(1 for i in all_issues if i[0] == "OK")
    
    print(f"\n{'='*80}")
    print(f"  ИТОГО: {ok} OK | {warnings} предупреждений | {errors} ошибок")
    print(f"{'='*80}")
    
    if errors > 0:
        print(f"\n  → Сначала исправьте {errors} ошибок")
    if warnings > 0:
        print(f"  → Затем обработайте {warnings} предупреждений")
    if errors == 0 and warnings == 0:
        print(f"\n  → Проект в отличном состоянии!")
    
    print()


if __name__ == "__main__":
    main()
