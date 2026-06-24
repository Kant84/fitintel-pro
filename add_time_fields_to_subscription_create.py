# add_time_fields_to_subscription_create.py
with open('app/services/subscription_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_subscription = '''        subscription = Subscription(
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
        )'''

new_subscription = '''        subscription = Subscription(
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

if old_subscription in content:
    content = content.replace(old_subscription, new_subscription)
    with open('app/services/subscription_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Временные ограничения добавлены в создание Subscription!")
else:
    print("ERROR: Не найдено создание Subscription")
