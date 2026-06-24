# add_time_fields_to_subscription.py
with open('app/models/subscription.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт Time
old_import = '''from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Text,
)'''
new_import = '''from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Time,
)'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем поля после last_renewed_at
old_fields = '''    last_renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # СВЯЗИ
    # =========================================================='''

new_fields = '''    last_renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ==========================================================
    # ВРЕМЕННЫЕ ОГРАНИЧЕНИЯ (дневной/ночной/полный день)
    # ==========================================================
    
    # Тип ограничения: FULLDAY, DAYTIME, NIGHTTIME
    time_restriction_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Время начала доступа (например, 06:00)
    allowed_start_time: Mapped[str | None] = mapped_column(
        Time,
        nullable=True,
    )
    
    # Время окончания доступа (например, 22:00)
    allowed_end_time: Mapped[str | None] = mapped_column(
        Time,
        nullable=True,
    )

    # ==========================================================
    # СВЯЗИ
    # =========================================================='''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/models/subscription.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля временных ограничений добавлены в Subscription!")
else:
    print("ERROR: Не найдены поля для вставки")
