# fix_tariff_service.py
with open('app/services/tariff_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Добавляем параметры в create_tariff
old_create_sig = '''    def create_tariff(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
        price: Decimal,
        currency: str,
        duration_days: int,
        visit_limit: int | None,
        is_unlimited: bool,
        is_active: bool,
        actor_user_id=None,
    ) -> Tariff:'''

new_create_sig = '''    def create_tariff(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
        price: Decimal,
        currency: str,
        duration_days: int,
        visit_limit: int | None,
        is_unlimited: bool,
        is_active: bool,
        promo_code: str | None = None,
        discount_percent: int | None = 0,
        actor_user_id=None,
    ) -> Tariff:'''

if old_create_sig in content:
    content = content.replace(old_create_sig, new_create_sig)
    print("Параметры добавлены в create_tariff!")
else:
    print("Не найдена сигнатура create_tariff")

# 2. Добавляем поля в создание ORM-объекта
old_tariff_create = '''        tariff = Tariff(
            code=normalized_code,
            name=normalized_name,
            description=normalized_description,
            price=validated_price,
            currency=normalized_currency,
            duration_days=validated_duration_days,
            visit_limit=resolved_visit_limit,
            is_unlimited=resolved_is_unlimited,
            is_active=is_active,
        )'''

new_tariff_create = '''        tariff = Tariff(
            code=normalized_code,
            name=normalized_name,
            description=normalized_description,
            price=validated_price,
            currency=normalized_currency,
            duration_days=validated_duration_days,
            visit_limit=resolved_visit_limit,
            is_unlimited=resolved_is_unlimited,
            is_active=is_active,
            promo_code=promo_code,
            discount_percent=discount_percent,
        )'''

if old_tariff_create in content:
    content = content.replace(old_tariff_create, new_tariff_create)
    print("Поля добавлены в создание тарифа!")
else:
    print("Не найдено создание Tariff")

# 3. Добавляем в audit after_data
old_audit = '''                "is_unlimited": created_tariff.is_unlimited,
                "is_active": created_tariff.is_active,
            },'''

new_audit = '''                "is_unlimited": created_tariff.is_unlimited,
                "is_active": created_tariff.is_active,
                "promo_code": created_tariff.promo_code,
                "discount_percent": created_tariff.discount_percent,
            },'''

if old_audit in content:
    content = content.replace(old_audit, new_audit)
    print("Audit обновлён!")
else:
    print("Не найден audit")

with open('app/services/tariff_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Готово!")
