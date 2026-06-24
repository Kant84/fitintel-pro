# fix_tariff_promo.py
import re

# 1. Модель БД
with open('app/models/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим место после is_active и добавляем поля
old_model = '''    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )'''

new_model = '''    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    promo_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    discount_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )'''

if old_model in content:
    content = content.replace(old_model, new_model)
    with open('app/models/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля promo_code и discount_percent добавлены в модель!")
else:
    print("Не найдено место в модели")

# 2. Схема TariffResponse
with open('app/schemas/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим is_active в TariffResponse и добавляем после него
old_response = '''    is_active: bool = Field(
        description="Активен ли тариф",
        examples=[True],
    )'''

new_response = '''    is_active: bool = Field(
        description="Активен ли тариф",
        examples=[True],
    )

    promo_code: str | None = Field(
        default=None,
        description="Промокод для скидки",
        examples=["SUMMER2026"],
    )

    discount_percent: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Процент скидки",
        examples=[10],
    )'''

if old_response in content:
    content = content.replace(old_response, new_response)
    print("Поля добавлены в TariffResponse!")
else:
    print("Не найдено место в TariffResponse")

# 3. Схема TariffCreateRequest
old_create = '''    is_active: bool | None = Field(
        default=True,
        description="Активен ли тариф",
        examples=[True],
    )'''

new_create = '''    is_active: bool | None = Field(
        default=True,
        description="Активен ли тариф",
        examples=[True],
    )

    promo_code: str | None = Field(
        default=None,
        max_length=50,
        description="Промокод для скидки",
        examples=["SUMMER2026"],
    )

    discount_percent: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Процент скидки",
        examples=[10],
    )'''

if old_create in content:
    content = content.replace(old_create, new_create)
    with open('app/schemas/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля добавлены в TariffCreateRequest!")
else:
    print("Не найдено место в TariffCreateRequest")

print("Готово! Нужно применить миграцию БД.")
