# fix_payment_endpoint.py
with open('app/api/v1/payments.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = '''    payment = service.create_payment(
        client_id=str(payload.client_id),
        amount=payload.amount,
        payment_method=payload.payment_method,
        payment_system=payload.payment_system,
        notes=payload.notes,
        return_url=payload.return_url,
        webhook_url=payload.webhook_url,
        actor_user_id=str(current_user.id),
    )'''

new_call = '''    payment = service.create_payment(
        client_id=str(payload.client_id),
        amount=payload.amount,
        payment_method=payload.payment_method,
        payment_system=payload.payment_system,
        notes=payload.notes,
        return_url=payload.return_url,
        webhook_url=payload.webhook_url,
        payment_direction=payload.payment_direction,
        payment_category=payload.payment_category,
        actor_user_id=str(current_user.id),
    )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/payments.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Endpoint обновлён!")
else:
    print("Не найден вызов create_payment")
