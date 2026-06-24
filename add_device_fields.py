# add_device_fields.py
with open('app/models/device.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем поля перед notes
old_notes = '''    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )'''

new_notes = '''    # Блокировка устройства
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Anti-passback включён
    anti_passback_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Рабочий график (JSON: {"start": "08:00", "end": "22:00"})
    work_schedule: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    
    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )'''

if old_notes in content:
    content = content.replace(old_notes, new_notes)
    with open('app/models/device.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля добавлены в Device!")
else:
    print("ERROR: Не найдены поля для вставки")
