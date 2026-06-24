# fix_payment_audit.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_audit = '''        self.audit.log(
            action="payment.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment created for client {client.email}: {amount} RUB",
            after_data={
                "payment_id": payment.id,
                "amount": str(amount),
                "method": payment_method.value,
            },
        )'''

new_audit = '''        client_info = client.email if client else "внутренний платёж"
        self.audit.log(
            action="payment.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=payment.id,
            message=f"Payment created for {client_info}: {amount} RUB",
            after_data={
                "payment_id": payment.id,
                "amount": str(amount),
                "method": payment_method.value,
                "direction": payment_direction,
                "category": payment_category,
            },
        )'''

if old_audit in content:
    content = content.replace(old_audit, new_audit)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Audit log исправлен!")
else:
    print("Не найден audit log")
