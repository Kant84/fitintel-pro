# fix_payment_service_create.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_create = '''    def create_payment(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        payment_system: PaymentSystem | None = None,
        notes: str | None = None,
        return_url: str | None = None,
        webhook_url: str | None = None,
        actor_user_id: str | None = None,
    ) -> Payment:'''

new_create = '''    def create_payment(
        self,
        client_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        payment_system: PaymentSystem | None = None,
        notes: str | None = None,
        return_url: str | None = None,
        webhook_url: str | None = None,
        payment_direction: str = "INCOME",
        payment_category: str = "SUBSCRIPTION",
        actor_user_id: str | None = None,
    ) -> Payment:'''

if old_create in content:
    content = content.replace(old_create, new_create)
    print("create_payment обновлён!")
else:
    print("Не найден create_payment")

# Находим создание Payment
old_payment = '''        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency="RUB",
            payment_method=payment_method.value,
            payment_system=payment_system.value if payment_system else None,
            status=PaymentStatus.PENDING.value,
            notes=notes,
            created_by_user_id=actor_user_id,
        )'''

new_payment = '''        payment = Payment(
            client_id=client_id,
            amount=amount,
            currency="RUB",
            payment_method=payment_method.value,
            payment_system=payment_system.value if payment_system else None,
            payment_direction=payment_direction,
            payment_category=payment_category,
            status=PaymentStatus.PENDING.value,
            notes=notes,
            created_by_user_id=actor_user_id,
        )'''

if old_payment in content:
    content = content.replace(old_payment, new_payment)
    print("Payment объект обновлён!")
else:
    print("Не найден Payment объект")

with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Готово!")
