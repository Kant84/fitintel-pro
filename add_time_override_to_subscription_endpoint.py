# add_time_override_to_subscription_endpoint.py
with open('app/api/v1/subscriptions.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = '''    subscription = subscription_service.create_subscription(
        client_id=str(payload.client_id),
        tariff_id=str(payload.tariff_id),
        start_date=payload.start_date,
        status_value=payload.status,
        notes=payload.notes,
        actor_user_id=current_user.id,
    )'''

new_call = '''    subscription = subscription_service.create_subscription(
        client_id=str(payload.client_id),
        tariff_id=str(payload.tariff_id),
        start_date=payload.start_date,
        status_value=payload.status,
        notes=payload.notes,
        actor_user_id=current_user.id,
        time_restriction_type=payload.time_restriction_type,
        allowed_start_time=payload.allowed_start_time,
        allowed_end_time=payload.allowed_end_time,
    )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/subscriptions.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Endpoint subscriptions.py обновлён — передача временных ограничений!")
else:
    print("ERROR: Не найден вызов create_subscription")
