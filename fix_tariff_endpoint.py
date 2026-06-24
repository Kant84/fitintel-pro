# fix_tariff_endpoint.py
with open('app/api/v1/tariffs.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = '''    tariff = tariff_service.create_tariff(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        duration_days=payload.duration_days,
        visit_limit=payload.visit_limit,
        is_unlimited=payload.is_unlimited,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )'''

new_call = '''    tariff = tariff_service.create_tariff(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        duration_days=payload.duration_days,
        visit_limit=payload.visit_limit,
        is_unlimited=payload.is_unlimited,
        is_active=payload.is_active,
        promo_code=payload.promo_code,
        discount_percent=payload.discount_percent,
        actor_user_id=current_user.id,
    )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/tariffs.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Endpoint обновлён!")
else:
    print("Не найден вызов create_tariff")
