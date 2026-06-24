# fix_payment_audit_v2.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_audit = '''        self.audit.log(
            action="payment.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=created_payment.id,
            message=f"Payment created for client {client.email}: {amount} RUB",
            after_data={
                "client_id": client_id,
                "amount": str(amount),
                "payment_method": payment_method.value,
                "payment_system": payment_system.value if payment_system else None,
            },
        )'''

new_audit = '''        client_info = client.email if client else "внутренний платёж"
        self.audit.log(
            action="payment.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="payment",
            entity_id=created_payment.id,
            message=f"Payment created for {client_info}: {amount} RUB",
            after_data={
                "client_id": client_id,
                "amount": str(amount),
                "payment_method": payment_method.value,
                "payment_system": payment_system.value if payment_system else None,
                "payment_direction": payment_direction,
                "payment_category": payment_category,
            },
        )'''

if old_audit in content:
    content = content.replace(old_audit, new_audit)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Audit log исправлен!")
else:
    print("Не найден audit log")
