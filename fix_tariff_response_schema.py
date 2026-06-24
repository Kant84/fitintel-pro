# fix_tariff_response_schema.py
with open('app/schemas/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_response = '''    # активность
    is_active: bool = Field(
        description="Активен ли тариф",
        examples=[True],
    )

    # дата создания
    created_at: datetime

    # дата обновления
    updated_at: datetime


# схема ответа списка тарифов'''

new_response = '''    # активность
    is_active: bool = Field(
        description="Активен ли тариф",
        examples=[True],
    )

    # промокод
    promo_code: str | None = Field(
        default=None,
        description="Промокод для скидки",
        examples=["SUMMER2026"],
    )

    # скидка
    discount_percent: int | None = Field(
        default=0,
        description="Процент скидки",
        examples=[10],
    )

    # дата создания
    created_at: datetime

    # дата обновления
    updated_at: datetime


# схема ответа списка тарифов'''

if old_response in content:
    content = content.replace(old_response, new_response)
    with open('app/schemas/tariff.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля добавлены в TariffResponse!")
else:
    print("Не найден конец TariffResponse")
