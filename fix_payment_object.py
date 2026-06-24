# fix_payment_object.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_payment = '''        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency="RUB",
            payment_method=payment_method.value,
            status=PaymentStatus.PENDING.value,
            payment_system=payment_system.value if payment_system else None,
            notes=notes,
            created_by_user_id=actor_user_id,
        )'''

new_payment = '''        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency="RUB",
            payment_method=payment_method.value,
            status=PaymentStatus.PENDING.value,
            payment_system=payment_system.value if payment_system else None,
            payment_direction=payment_direction,
            payment_category=payment_category,
            notes=notes,
            created_by_user_id=actor_user_id,
        )'''

if old_payment in content:
    content = content.replace(old_payment, new_payment)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Payment объект обновлён!")
else:
    print("Не найден Payment объект")
