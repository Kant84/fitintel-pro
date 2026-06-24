# add_time_override_to_subscription_service.py
with open('app/services/subscription_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Обновляем сигнатуру create_subscription
old_sig = '''    def create_subscription(
        self,
        *,
        client_id: str,
        tariff_id: str,
        start_date,
        status_value: str,
        notes: str | None,
        actor_user_id=None,
    ) -> Subscription:'''

new_sig = '''    def create_subscription(
        self,
        *,
        client_id: str,
        tariff_id: str,
        start_date,
        status_value: str,
        notes: str | None,
        actor_user_id=None,
        time_restriction_type: str | None = None,
        allowed_start_time=None,
        allowed_end_time=None,
    ) -> Subscription:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("1. Сигнатура create_subscription обновлена!")
else:
    print("ERROR 1: Не найдена сигнатура")

# 2. Добавляем переопределение времени перед созданием Subscription
old_create = '''        # создаём абонемент
        subscription = Subscription(
            client_id=client.id,
            tariff_id=tariff.id,
            status=normalized_status,
            start_date=start_date,
            end_date=end_date,
            price=tariff.price,
            currency=tariff.currency,
            visit_limit=tariff.visit_limit,
            visits_used=0,
            is_unlimited=tariff.is_unlimited,
            is_active=resolved_is_active,
            notes=normalized_notes,
            time_restriction_type=tariff.time_restriction_type,
            allowed_start_time=tariff.allowed_start_time,
            allowed_end_time=tariff.allowed_end_time,
        )'''

new_create = '''        # определяем временные ограничения (переопределение или из тарифа)
        resolved_time_restriction_type = time_restriction_type if time_restriction_type is not None else tariff.time_restriction_type
        resolved_allowed_start_time = allowed_start_time if allowed_start_time is not None else tariff.allowed_start_time
        resolved_allowed_end_time = allowed_end_time if allowed_end_time is not None else tariff.allowed_end_time
        
        # создаём абонемент
        subscription = Subscription(
            client_id=client.id,
            tariff_id=tariff.id,
            status=normalized_status,
            start_date=start_date,
            end_date=end_date,
            price=tariff.price,
            currency=tariff.currency,
            visit_limit=tariff.visit_limit,
            visits_used=0,
            is_unlimited=tariff.is_unlimited,
            is_active=resolved_is_active,
            notes=normalized_notes,
            time_restriction_type=resolved_time_restriction_type,
            allowed_start_time=resolved_allowed_start_time,
            allowed_end_time=resolved_allowed_end_time,
        )'''

if old_create in content:
    content = content.replace(old_create, new_create)
    print("2. Переопределение времени добавлено в create_subscription!")
else:
    print("ERROR 2: Не найдено создание Subscription")

with open('app/services/subscription_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
