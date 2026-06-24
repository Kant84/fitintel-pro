# add_time_fields_to_tariff.py
with open('app/models/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт Time
old_import = '''from sqlalchemy import String, Boolean, Integer, Numeric, UniqueConstraint, Text'''
new_import = '''from sqlalchemy import String, Boolean, Integer, Numeric, UniqueConstraint, Text, Time'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем поля после discount_percent
old_fields = '''    discount_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )

    # ✅ ДОБАВИТЬ СВЯЗЬ С АБОНЕМЕНТАМИ'''

new_fields = '''    discount_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )

    # Временные ограничения (дневной/ночной/полный день)
    time_restriction_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="FULLDAY",
    )

    # Время начала доступа (например, 06:00 для дневного)
    allowed_start_time: Mapped[str | None] = mapped_column(
        Time,
        nullable=True,
    )

    # Время окончания доступа (например, 22:00 для дневного)
    allowed_end_time: Mapped[str | None] = mapped_column(
        Time,
        nullable=True,
    )

    # ✅ ДОБАВИТЬ СВЯЗЬ С АБОНЕМЕНТАМИ'''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/models/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля временных ограничений добавлены в Tariff!")
else:
    print("ERROR: Не найдены поля для вставки")
