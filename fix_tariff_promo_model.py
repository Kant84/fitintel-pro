# fix_tariff_promo_model.py
with open('app/models/tariff.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_model = '''    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )'''

new_model = '''    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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
    print("Поля добавлены в модель!")
else:
    print("Не найдено место в модели")
