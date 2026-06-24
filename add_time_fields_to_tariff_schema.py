# add_time_fields_to_tariff_schema.py
with open('app/schemas/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт time
old_import = '''from pydantic import BaseModel, Field, ConfigDict'''
new_import = '''from pydantic import BaseModel, Field, ConfigDict
from datetime import time'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем поля в TariffCreateRequest
old_fields = '''    # процент скидки
    discount_percent: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Процент скидки",
        examples=[10],
    )'''

new_fields = '''    # процент скидки
    discount_percent: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Процент скидки",
        examples=[10],
    )

    # тип временного ограничения
    time_restriction_type: str | None = Field(
        default="FULLDAY",
        description="Тип временного ограничения: FULLDAY, DAYTIME, NIGHTTIME",
        examples=["DAYTIME"],
    )

    # время начала доступа
    allowed_start_time: time | None = Field(
        default=None,
        description="Время начала доступа (например, 06:00 для дневного)",
        examples=["06:00"],
    )

    # время окончания доступа
    allowed_end_time: time | None = Field(
        default=None,
        description="Время окончания доступа (например, 22:00 для дневного)",
        examples=["22:00"],
    )'''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/schemas/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля временных ограничений добавлены в TariffCreateRequest!")
else:
    print("ERROR: Не найдены поля для вставки")
