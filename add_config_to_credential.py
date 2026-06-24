# add_config_to_credential.py
with open('app/models/credential.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт JSON
old_import = '''from sqlalchemy import String, Text, Date, DateTime'''
new_import = '''from sqlalchemy import String, Text, Date, DateTime, JSON'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем поле config перед notes
old_notes = '''    # Заметки
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )'''

new_notes = '''    # Дополнительные параметры (JSON: MIFARE, конфиг устройства)
    config: Mapped[dict | None] = mapped_column(
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
    with open('app/models/credential.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поле config добавлено в Credential!")
else:
    print("ERROR: Не найдены поля для вставки")
