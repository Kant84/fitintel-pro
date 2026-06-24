# fix_tariff_schema.py
with open('app/schemas/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим конец TariffCreateRequest
old_end = '''    # активен ли тариф
    is_active: bool = Field(
        default=True,
        description="Активен ли тариф",
        examples=[True],
    )


# схема обновления тарифа'''

new_end = '''    # активен ли тариф
    is_active: bool = Field(
        default=True,
        description="Активен ли тариф",
        examples=[True],
    )

    # промокод
    promo_code: str | None = Field(
        default=None,
        max_length=50,
        description="Промокод для скидки",
        examples=["SUMMER2026"],
    )

    # процент скидки
    discount_percent: int | None = Field(
        default=0,
        ge=0,
        le=100,
        description="Процент скидки",
        examples=[10],
    )


# схема обновления тарифа'''

if old_end in content:
    content = content.replace(old_end, new_end)
    with open('app/schemas/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля добавлены в TariffCreateRequest!")
else:
    print("Не найден конец TariffCreateRequest")
