# fix_tariff_time_fields.py
with open('app/services/tariff_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Добавляем параметры в сигнатуру create_tariff
old_sig = '''    def create_tariff(
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

new_sig = '''    def create_tariff(
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
        time_restriction_type: str | None = None,
        allowed_start_time=None,
        allowed_end_time=None,
        actor_user_id=None,
    ) -> Tariff:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("1. Сигнатура create_tariff обновлена!")
else:
    print("ERROR 1: Не найдена сигнатура")

# 2. Добавляем поля в создание Tariff
old_tariff = '''            is_active=is_active,
            promo_code=promo_code,
            discount_percent=discount_percent,
        )'''

new_tariff = '''            is_active=is_active,
            promo_code=promo_code,
            discount_percent=discount_percent,
            time_restriction_type=time_restriction_type,
            allowed_start_time=allowed_start_time,
            allowed_end_time=allowed_end_time,
        )'''

if old_tariff in content:
    content = content.replace(old_tariff, new_tariff)
    print("2. Поля временных ограничений добавлены в Tariff!")
else:
    print("ERROR 2: Не найдено создание Tariff")

# 3. Добавляем поля в audit after_data
old_audit = '''                "visit_limit": created_tariff.visit_limit,
                "is_unlimited": created_tariff.is_unlimited,'''

new_audit = '''                "visit_limit": created_tariff.visit_limit,
                "is_unlimited": created_tariff.is_unlimited,
                "time_restriction_type": created_tariff.time_restriction_type,
                "allowed_start_time": str(created_tariff.allowed_start_time) if created_tariff.allowed_start_time else None,
                "allowed_end_time": str(created_tariff.allowed_end_time) if created_tariff.allowed_end_time else None,'''

if old_audit in content:
    content = content.replace(old_audit, new_audit)
    print("3. Audit обновлён!")
else:
    print("ERROR 3: Не найден audit")

with open('app/services/tariff_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
