# fix_uuid_model.py
with open('app/models/hardware_device.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Меняем id на UUID
old_id = '''    id: Mapped[str] = mapped_column(String(36), primary_key=True)'''
new_id = '''    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))'''

if old_id in content:
    content = content.replace(old_id, new_id)
    # Добавляем import uuid
    if 'import uuid' not in content:
        content = 'import uuid\\n' + content
    with open('app/models/hardware_device.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Модель исправлена!")
else:
    print("Не найдено поле id")

# Исправляем print_service.py — убираем uuid.uuid4()
with open('app/services/print_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_uuid = '''        import uuid
        
        # Если устройство не указано — берём по умолчанию
        if not device_id:
            default_printer = self.get_default_printer()
            if default_printer:
                device_id = str(default_printer.id)
        
        job = PrintJob(
            id=str(uuid.uuid4()),'''

new_uuid = '''        # Если устройство не указано — берём по умолчанию
        if not device_id:
            default_printer = self.get_default_printer()
            if default_printer:
                device_id = str(default_printer.id)
        
        job = PrintJob('''

if old_uuid in content:
    content = content.replace(old_uuid, new_uuid)
    with open('app/services/print_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("PrintService исправлен!")
else:
    print("Не найден uuid в PrintService")
