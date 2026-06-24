# add_face_confidence.py
with open('app/models/credential.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_fields = '''    rfid_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # ==========================================================
    # ДОПОЛНИТЕЛЬНО
    # =========================================================='''

new_fields = '''    rfid_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # ==========================================================
    # ДЛЯ FACE ID
    # ==========================================================
    
    # Уверенность распознавания (0.0 - 1.0)
    face_confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    
    # Шаблон лица (base64 или ссылка на хранилище)
    face_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ==========================================================
    # ДОПОЛНИТЕЛЬНО
    # =========================================================='''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/models/credential.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля face_confidence и face_template добавлены!")
else:
    print("ERROR: Не найдены поля для вставки")
    # Пробуем найти с точным совпадением
    import re
    pattern = r'rfid_model: Mapped\[str \| None\] = mapped_column\(\s+String\(100\),\s+nullable=True,\s+\)\s+# =+\s+# ДОПОЛНИТЕЛЬНО\s+# =+'
    if re.search(pattern, content):
        print("Найдено по regex!")
    else:
        print("Не найдено по regex")
