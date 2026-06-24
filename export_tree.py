import os
from pathlib import Path

def format_size(size_bytes):
    """Преобразует байты в человекочитаемый формат"""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:6.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:6.1f} TB"

def get_dir_size(path):
    """Рекурсивно считает размер папки"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    except (PermissionError, OSError):
        pass
    return total

def tree(dir_path=".", prefix="", output_file="project_tree.txt", ignore=None):
    """Рекурсивно обходит и записывает дерево проекта"""
    if ignore is None:
        ignore = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache', '.idea', '.vscode'}
    
    path = Path(dir_path)
    
    try:
        entries = list(path.iterdir())
    except PermissionError:
        return
    
    # Сортируем: сначала папки, потом файлы
    entries.sort(key=lambda e: (e.is_file(), e.name.lower()))
    
    for i, entry in enumerate(entries):
        if entry.name in ignore:
            continue
            
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        
        if entry.is_dir():
            size = get_dir_size(entry)
            size_str = format_size(size)
            line = f"{prefix}{connector}📁 {entry.name}/  [{size_str}]"
        else:
            size = entry.stat().st_size
            size_str = format_size(size)
            line = f"{prefix}{connector}📄 {entry.name}  ({size_str})"
        
        print(line)
        output_lines.append(line)
        
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            tree(entry, prefix + extension, ignore=ignore)

# === ЗАПУСК ===
if __name__ == "__main__":
    output_lines = []
    
    # Заголовок
    root_name = Path(".").resolve().name
    header = f"🗂️  Проект: {root_name}\n📍 Путь: {Path('.').resolve()}\n{'='*60}\n"
    print(header)
    output_lines.append(header)
    
    # Собираем дерево
    tree(".")
    
    # Сохраняем в файл
    with open("project_tree.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    
    print(f"\n✅ Дерево сохранено в: project_tree.txt")