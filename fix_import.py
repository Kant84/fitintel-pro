# fix_import.py
with open('app/models/hardware_device.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем \n на реальный перенос
content = content.replace('import uuid\\nfrom datetime', 'import uuid\nfrom datetime')

with open('app/models/hardware_device.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Исправлено!")
