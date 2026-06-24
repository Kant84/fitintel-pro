# fix_win32_import.py
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем глобальный импорт в начало
if 'import win32print' not in content[:500]:
    old_import = 'from app.models.hardware_device import HardwareDevice, PrintJob'
    new_import = '''import win32print
import win32gui
import win32con
from app.models.hardware_device import HardwareDevice, PrintJob'''
    
    content = content.replace(old_import, new_import)
    
    # Убираем локальные импорты win32print
    content = content.replace('        import win32print\n', '')
    content = content.replace('        import win32gui\n', '')
    content = content.replace('        import win32con\n', '')
    
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорты исправлены!")
else:
    print("Импорты уже есть")
